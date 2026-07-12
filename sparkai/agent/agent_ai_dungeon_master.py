"""
SparkLabs Agent - AI Dungeon Master

A singleton AI Dungeon Master agent that orchestrates tabletop-style RPG
gameplay for the SparkLabs AI-native game engine. The Dungeon Master weaves
adaptive narratives, roleplays non-player characters, adjudicates rules, and
maintains a living world state that responds to player agency.

Core design principles:
  - The world is alive: factions shift, seasons turn, and consequences ripple
    through the campaign long after the choice that spawned them.
  - Story arcs are woven, not scripted: each arc progresses through narrative
    beats that adapt to player decisions and moral alignments.
  - NPCs are characters, not props: every NPC has personality, backstory,
    secrets, and a relationship with the party that evolves over time.
  - Moral choices have weight: decisions produce consequences that are
    narrative, mechanical, and world-altering, tracked permanently when flagged.
  - Encounters scale to the party: difficulty, rewards, and enemy composition
    adapt to party level, size, and composition.
  - The DM adjudicates fairly: rule calls combine dice mechanics with narrative
    context to produce rulings that feel earned and consistent.
  - Sessions are persistent: every campaign, arc, NPC, encounter, and choice is
    tracked across sessions, enabling long-form storytelling.

Architecture:
  AIDungeonMaster (singleton)
    |-- CampaignType, StoryArcType, NPCRole, AlignmentType, MoralChoiceType,
    |   ConsequenceType, EncounterDifficulty, PartyRole, CampaignStatus,
    |   DungeonMasterEventKind
    |-- Campaign, StoryArc, NPCProfile, MoralChoice, Consequence, Encounter,
    |   PartyMember, WorldState, DungeonMasterConfig, DungeonMasterStats,
    |   DungeonMasterSnapshot, DungeonMasterEvent
    |-- get_dungeon_master

Core Capabilities:
  - register_campaign / get_campaign / list_campaigns / remove_campaign:
    campaign lifecycle management with rich metadata, tone, and DM style.
  - register_story_arc / get_story_arc / list_story_arcs / remove_story_arc /
    advance_story_arc: multi-arc story weaving with objective tracking and
    NPC and location linkage.
  - register_npc / get_npc / list_npcs / remove_npc / set_npc_relationship:
    NPC roster management with alignment, personality, secrets, and evolving
    relationship levels.
  - register_moral_choice / get_moral_choice / list_moral_choices /
    resolve_moral_choice / apply_consequence: branching moral decision system
    with permanent and temporary consequences.
  - register_encounter / get_encounter / list_encounters / complete_encounter /
    scale_encounter: encounter design and runtime scaling with reward tracking.
  - register_party_member / get_party_member / list_party_members /
    remove_party_member: party roster with stats, inventory, and HP tracking.
  - get_world_state / update_world_state: living world state with faction
    power, location states, global flags, time, weather, and seasons.
  - generate_narrative / adjudicate_rule / calculate_encounter_difficulty:
    AI-driven narrative generation, rule adjudication, and difficulty calculus.
  - tick / get_status / reset / get_snapshot / get_stats / set_config /
    get_config / list_events: observability, lifecycle, and tuning.
"""

from __future__ import annotations

import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Module-Level Singleton Lock and Instance
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_instance = None


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_STORY_ARCS: int = 2000
_MAX_NPCS: int = 3000
_MAX_MORAL_CHOICES: int = 2000
_MAX_CONSEQUENCES: int = 3000
_MAX_ENCOUNTERS: int = 2000
_MAX_PARTY_MEMBERS: int = 1000
_MAX_WORLD_STATES: int = 500
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return an ISO 8601 UTC timestamp string."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
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


def _to_jsonable(value: Any) -> Any:
    """Convert arbitrary values into JSON-serializable forms.

    The __dataclass_fields__ attribute is checked BEFORE any to_dict fallback
    so that a dataclass whose to_dict() calls _dataclass_to_dict cannot enter
    an infinite recursion loop.
    """
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
    """Convert a dataclass instance into a JSON-friendly dict.

    Checks __dataclass_fields__ BEFORE to_dict to avoid recursion: when a
    dataclass defines to_dict() that delegates back to _dataclass_to_dict,
    the field inspection short-circuits the cycle.
    """
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CampaignType(str, Enum):
    """Classification of campaign frameworks."""
    EPIC_QUEST = "epic_quest"
    SANDBOX = "sandbox"
    DUNGEON_CRAWL = "dungeon_crawl"
    POLITICAL_INTRIGUE = "political_intrigue"
    SURVIVAL = "survival"
    MYSTERY = "mystery"
    WAR_CAMPAIGN = "war_campaign"
    EXPLORATION = "exploration"


class StoryArcType(str, Enum):
    """Narrative arc phases within a campaign."""
    INTRODUCTION = "introduction"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    SIDE_QUEST = "side_quest"
    INTERLUDE = "interlude"


class NPCRole(str, Enum):
    """Functional role of a non-player character."""
    ALLY = "ally"
    VILLAIN = "villain"
    MENTOR = "mentor"
    MERCHANT = "merchant"
    QUEST_GIVER = "quest_giver"
    BACKGROUND = "background"
    RECURRING = "recurring"
    BOSS = "boss"
    HENCHMAN = "henchman"
    NEUTRAL = "neutral"


class AlignmentType(str, Enum):
    """Moral and ethical alignment spectrum."""
    LAWFUL_GOOD = "lawful_good"
    NEUTRAL_GOOD = "neutral_good"
    CHAOTIC_GOOD = "chaotic_good"
    LAWFUL_NEUTRAL = "lawful_neutral"
    TRUE_NEUTRAL = "true_neutral"
    CHAOTIC_NEUTRAL = "chaotic_neutral"
    LAWFUL_EVIL = "lawful_evil"
    NEUTRAL_EVIL = "neutral_evil"
    CHAOTIC_EVIL = "chaotic_evil"


class MoralChoiceType(str, Enum):
    """Category of a moral dilemma."""
    GOOD_VS_EVIL = "good_vs_evil"
    LAW_VS_CHAOS = "law_vs_chaos"
    SELF_VS_OTHERS = "self_vs_others"
    SHORT_VS_LONG = "short_vs_long"
    TRUTH_VS_LIES = "truth_vs_lies"
    MERCY_VS_JUSTICE = "mercy_vs_justice"


class ConsequenceType(str, Enum):
    """Classification of choice consequences."""
    NARRATIVE = "narrative"
    MECHANICAL = "mechanical"
    REPUTATION = "reputation"
    RELATIONSHIP = "relationship"
    WORLD_STATE = "world_state"
    ITEM_GAIN = "item_gain"
    ITEM_LOSS = "item_loss"
    ABILITY_GAIN = "ability_gain"


class EncounterDifficulty(str, Enum):
    """Difficulty tiers for encounters."""
    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    DEADLY = "deadly"
    BOSS = "boss"


class PartyRole(str, Enum):
    """Combat and social role within an adventuring party."""
    LEADER = "leader"
    STRATEGIST = "strategist"
    DIPLOMAT = "diplomat"
    SCOUT = "scout"
    HEALER = "healer"
    TANK = "tank"
    DAMAGE_DEALER = "damage_dealer"
    UTILITY = "utility"


class CampaignStatus(str, Enum):
    """Lifecycle status of a campaign."""
    PREPARING = "preparing"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DungeonMasterEventKind(str, Enum):
    """Audit event kinds emitted by the Dungeon Master."""
    CAMPAIGN_STARTED = "campaign_started"
    QUEST_ASSIGNED = "quest_assigned"
    NPC_INTRODUCED = "npc_introduced"
    STORY_BEAT = "story_beat"
    MORAL_CHOICE = "moral_choice"
    ENCOUNTER_TRIGGERED = "encounter_triggered"
    PLAYER_ACTION = "player_action"
    CONSEQUENCE_APPLIED = "consequence_applied"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Campaign:
    """A tabletop RPG campaign managed by the Dungeon Master."""
    campaign_id: str
    name: str
    type: str
    description: str = ""
    dm_style: str = "balanced"
    setting: str = ""
    tone: str = "heroic"
    starting_level: int = 1
    max_players: int = 6
    status: str = CampaignStatus.PREPARING.value
    session_count: int = 0
    current_arc: str = ""
    story_arcs: List[str] = field(default_factory=list)
    player_ids: List[str] = field(default_factory=list)
    world_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StoryArc:
    """A narrative arc within a campaign."""
    arc_id: str
    campaign_id: str
    arc_type: str
    title: str
    description: str = ""
    objectives: List[str] = field(default_factory=list)
    key_npcs: List[str] = field(default_factory=list)
    key_locations: List[str] = field(default_factory=list)
    moral_choices: List[str] = field(default_factory=list)
    is_resolved: bool = False
    resolution: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NPCProfile:
    """A non-player character with personality, history, and relationships."""
    npc_id: str
    name: str
    role: str
    alignment: str
    race: str = ""
    class_name: str = ""
    personality_traits: List[str] = field(default_factory=list)
    appearance: str = ""
    backstory: str = ""
    relationship_level: int = 0
    is_alive: bool = True
    location_id: str = ""
    quest_ids: List[str] = field(default_factory=list)
    dialogue_topics: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MoralChoice:
    """A branching moral dilemma presented to the players."""
    choice_id: str
    arc_id: str
    description: str
    choice_type: str
    options: List[Dict[str, Any]] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    player_choice: str = ""
    is_resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Consequence:
    """A concrete outcome resulting from a moral choice."""
    consequence_id: str
    choice_id: str
    type: str
    description: str
    affected_entities: List[str] = field(default_factory=list)
    magnitude: int = 0
    is_permanent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Encounter:
    """A combat or social encounter with scaling and rewards."""
    encounter_id: str
    campaign_id: str
    difficulty: str
    description: str = ""
    enemy_ids: List[str] = field(default_factory=list)
    location_id: str = ""
    reward_xp: int = 0
    reward_items: List[str] = field(default_factory=list)
    is_completed: bool = False
    trigger_condition: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PartyMember:
    """A player character within a campaign party."""
    member_id: str
    player_id: str
    campaign_id: str
    character_name: str
    race: str
    class_name: str
    level: int = 1
    party_role: str = PartyRole.UTILITY.value
    alignment: str = AlignmentType.TRUE_NEUTRAL.value
    backstory: str = ""
    current_hp: int = 0
    max_hp: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WorldState:
    """The living, evolving state of a campaign world."""
    state_id: str
    campaign_id: str
    faction_power: Dict[str, int] = field(default_factory=dict)
    location_states: Dict[str, str] = field(default_factory=dict)
    global_flags: Dict[str, bool] = field(default_factory=dict)
    time_elapsed: float = 0.0
    day_count: int = 0
    weather: str = "clear"
    season: str = "spring"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonMasterConfig:
    """Global tuning parameters for the Dungeon Master."""
    max_campaigns: int = 10
    max_npcs_per_campaign: int = 50
    max_party_size: int = 6
    story_complexity: str = "medium"
    moral_system_enabled: bool = True
    permadeath: bool = False
    auto_balance_encounters: bool = True
    session_timeout: int = 240

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonMasterStats:
    """Aggregate runtime statistics."""
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_npcs: int = 0
    total_encounters: int = 0
    moral_choices_made: int = 0
    sessions_run: int = 0
    avg_session_length: float = 0.0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonMasterSnapshot:
    """A point-in-time snapshot of the Dungeon Master state."""
    timestamp: str
    campaigns_count: int
    active_campaigns: int
    npcs_count: int
    encounters_count: int
    parties_count: int
    config: DungeonMasterConfig = field(default_factory=DungeonMasterConfig)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonMasterEvent:
    """An audit event emitted by the Dungeon Master."""
    event_id: str
    kind: str
    timestamp: str
    campaign_id: str = ""
    session_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Dungeon Master
# ---------------------------------------------------------------------------


class AIDungeonMaster:
    """AI-powered Dungeon Master that orchestrates RPG campaigns.

    Implements a singleton via module-level double-checked locking. All
    mutations to internal state are guarded by the module-level _lock so the
    Dungeon Master is safe to call from multiple threads.
    """

    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._campaigns: Dict[str, Campaign] = {}
        self._story_arcs: Dict[str, StoryArc] = {}
        self._npcs: Dict[str, NPCProfile] = {}
        self._moral_choices: Dict[str, MoralChoice] = {}
        self._consequences: Dict[str, Consequence] = {}
        self._encounters: Dict[str, Encounter] = {}
        self._parties: Dict[str, PartyMember] = {}
        self._world_states: Dict[str, WorldState] = {}
        self._events: List[DungeonMasterEvent] = []
        self._applied_consequences: set = set()
        self._config = DungeonMasterConfig()
        self._stats = DungeonMasterStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._seed()

    @classmethod
    def get_instance(cls) -> "AIDungeonMaster":
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # -- Campaigns ------------------------------------------------
            self._campaigns["cmp_shattered_crown"] = Campaign(
                campaign_id="cmp_shattered_crown",
                name="The Shattered Crown",
                type=CampaignType.EPIC_QUEST.value,
                description="The kingdom of Aethelgard fractures as King Aldric "
                            "descends into tyranny. A band of heroes must unite the "
                            "shattered remnants of the realm before all is consumed "
                            "by civil war and darker things that stir beneath the throne.",
                dm_style="dramatic",
                setting="High fantasy kingdom of Aethelgard",
                tone="heroic",
                starting_level=5,
                max_players=6,
                status=CampaignStatus.ACTIVE.value,
                session_count=3,
                current_arc="arc_crown_betrayal",
                metadata={"theme": "loyalty", "language": "common"},
            )
            self._campaigns["cmp_neon_shadows"] = Campaign(
                campaign_id="cmp_neon_shadows",
                name="Neon Shadows",
                type=CampaignType.POLITICAL_INTRIGUE.value,
                description="In the sprawl of Neo-Veridia, corporations rule from "
                            "glass towers while the streets below churn with data "
                            "thieves, chrome mercenaries, and revolutionaries. The "
                            "party is caught between rival factions fighting over a "
                            "data shard that could rewrite the city's power structure.",
                dm_style="gritty",
                setting="Cyberpunk megacity of Neo-Veridia",
                tone="noir",
                starting_level=3,
                max_players=5,
                status=CampaignStatus.ACTIVE.value,
                session_count=2,
                current_arc="arc_neon_conspiracy",
                metadata={"theme": "power", "currency": "credits"},
            )
            self._campaigns["cmp_void_expedition"] = Campaign(
                campaign_id="cmp_void_expedition",
                name="The Void Expedition",
                type=CampaignType.DUNGEON_CRAWL.value,
                description="A deep-space expedition descends into an abandoned "
                            "xeno-archaeological site on the rim of charted space. "
                            "What the crew finds below the surface is not dead, merely "
                            "waiting. Survival becomes the only quest that matters.",
                dm_style="survival_horror",
                setting="Sci-fi derelict station in the Veil Expanse",
                tone="dark",
                starting_level=4,
                max_players=4,
                status=CampaignStatus.ACTIVE.value,
                session_count=1,
                current_arc="arc_void_descent",
                metadata={"theme": "survival", "tech_level": "far_future"},
            )

            # -- Story Arcs -----------------------------------------------
            crown = "cmp_shattered_crown"
            neon = "cmp_neon_shadows"
            void = "cmp_void_expedition"

            arc_specs = [
                ("arc_crown_intro", crown, StoryArcType.INTRODUCTION.value,
                 "The Coronation Crisis",
                 "King Aldric's coronation is interrupted by an assassination attempt "
                 "that reveals a plot far deeper than anyone imagined.",
                 ["Attend the coronation of King Aldric",
                  "Investigate the assassination attempt",
                  "Discover the identity of the conspirators"],
                 ["npc_king_aldric", "npc_sage_merlin", "npc_quest_giver_farmer"],
                 ["Throne Room", "Royal Archive", "Market District"]),
                ("arc_crown_betrayal", crown, StoryArcType.RISING_ACTION.value,
                 "The Betrayal at Highreach",
                 "A trusted ally turns against the party, revealing that the conspiracy "
                 "reaches into the heart of the royal court.",
                 ["Travel to Highreach Keep",
                  "Unmask the traitor within the court",
                  "Decide the fate of a captured hostage"],
                 ["npc_king_aldric", "npc_thief_raven", "npc_henchman_grunt"],
                 ["Highreach Keep", "Dungeon of Highreach"]),
                ("arc_crown_climax", crown, StoryArcType.CLIMAX.value,
                 "The Throne of Blood",
                 "The party storms the throne room to confront King Aldric and end "
                 "his reign of terror once and for all.",
                 ["Breaching the inner sanctum",
                  "Defeat King Aldric's royal guard",
                  "Confront King Aldric on the throne"],
                 ["npc_king_aldric", "npc_sage_merlin", "npc_merchant_gilda"],
                 ["Throne Room", "Royal Armory"]),
                ("arc_neon_startup", neon, StoryArcType.INTRODUCTION.value,
                 "The Contract",
                 "A mysterious fixer hires the party for a seemingly simple data "
                 "retrieval job that spirals into a corporate war.",
                 ["Meet the fixer at the rooftop bar",
                  "Retrieve the data shard from the lab",
                  "Deliver the shard to the contact"],
                 ["npc_captain_reyes", "npc_diplomat_vezra", "npc_background_innkeeper"],
                 ["Rooftop Bar", "Corporate Lab"]),
                ("arc_neon_conspiracy", neon, StoryArcType.RISING_ACTION.value,
                 "The Conspiracy Deepens",
                 "The data shard reveals a conspiracy that could topple Neo-Veridia's "
                 "most powerful corporation. Now everyone wants the party dead.",
                 ["Decrypt the data shard",
                  "Infiltrate the corporate server farm",
                  "Decide whether to expose or bury the truth"],
                 ["npc_captain_reyes", "npc_smuggler_jax", "npc_henchman_grunt"],
                 ["Server Farm", "Underground Market"]),
                ("arc_neon_revelation", neon, StoryArcType.CLIMAX.value,
                 "The Revelation",
                 "The conspiracy's mastermind is revealed, and the party must choose "
                 "between loyalty, justice, and survival.",
                 ["Confront the mastermind",
                  "Navigate the loyalty divide within the party",
                  "Decide the fate of Neo-Veridia"],
                 ["npc_quemada_boss", "npc_diplomat_vezra", "npc_smuggler_jax"],
                 ["Quemada Tower", "Neon Plaza"]),
                ("arc_void_descent", void, StoryArcType.INTRODUCTION.value,
                 "Descent into the Derelict",
                 "The expedition crew enters the abandoned xeno-archaeological site "
                 "and discovers that the station is not as empty as reported.",
                 ["Establish a base camp",
                  "Map the upper decks",
                  "Investigate the anomalous signal"],
                 ["npc_scientist_vale", "npc_spirit_guide", "npc_mystic_ora"],
                 ["Upper Decks", "Base Camp"]),
                ("arc_void_abyss", void, StoryArcType.RISING_ACTION.value,
                 "The Abyss Below",
                 "The crew descends into the station's deepest levels, where the "
                 "architecture defies human engineering and something ancient stirs.",
                 ["Descend to the lower levels",
                  "Survive the abyssal horror",
                  "Decide whether to sacrifice a crew member for passage"],
                 ["npc_warlord_drax", "npc_scientist_vale", "npc_spirit_guide"],
                 ["Abyssal Level", "Xeno-Forge"]),
                ("arc_void_escape", void, StoryArcType.CLIMAX.value,
                 "Escape from the Void",
                 "With the truth uncovered, the surviving crew must fight their way "
                 "back to the surface before the station is consumed entirely.",
                 ["Fight through the collapsing station",
                  "Reach the escape pods",
                  "Decide what knowledge to bring back"],
                 ["npc_warlord_drax", "npc_mystic_ora", "npc_spirit_guide"],
                 ["Escape Bay", "Collapsed Corridors"]),
                ("arc_void_sidequest", void, StoryArcType.SIDE_QUEST.value,
                 "The Lost Log",
                 "A detour to recover a lost research log reveals the station's "
                 "original purpose and the fate of its crew.",
                 ["Locate the research log",
                  "Decode the encrypted entries",
                  "Decide whether to share the findings"],
                 ["npc_scientist_vale", "npc_background_innkeeper"],
                 ["Archive Room"]),
            ]
            for arc_id, camp, atype, title, desc, objs, npcs, locs in arc_specs:
                arc = StoryArc(
                    arc_id=arc_id, campaign_id=camp, arc_type=atype,
                    title=title, description=desc,
                    objectives=objs, key_npcs=npcs, key_locations=locs,
                )
                self._story_arcs[arc_id] = arc
                if camp in self._campaigns:
                    self._campaigns[camp].story_arcs.append(arc_id)

            # -- NPCs -----------------------------------------------------
            npc_specs = [
                ("npc_king_aldric", "King Aldric the Iron-Handed",
                 NPCRole.VILLAIN.value, AlignmentType.LAWFUL_EVIL.value,
                 "Human", "Aristocrat",
                 ["ruthless", "paranoid", "eloquent", "obsessed with order"],
                 "A tall, gaunt man with a crown of black iron and eyes that "
                 "have not known warmth in years. His robes are regal but stained.",
                 "Once a just king, Aldric was broken by a failed coup that killed "
                 "his family. He now rules through fear, convinced that mercy is "
                 "weakness. His descent into tyranny was gradual but absolute.",
                 -80, "loc_throne_room",
                 ["quest_stop_aldric", "quest_save_hostages"],
                 ["the crown", "the coup", "his family", "the rebellion"],
                 ["He secretly keeps his daughter alive in a hidden tower, "
                  "unable to kill the last of his blood."]),
                ("npc_sage_merlin", "Sage Merlin the Wise",
                 NPCRole.MENTOR.value, AlignmentType.LAWFUL_GOOD.value,
                 "Human", "Wizard",
                 ["patient", "cryptic", "kind", "burdened by knowledge"],
                 "An elderly man with a long silver beard and robes covered in "
                 "astral symbols. His eyes gleam with arcane light.",
                 "Merlin has guided heroes for centuries, extending his life through "
                 "magic. He trained the party and sees them as his last hope.",
                 70, "loc_sage_tower",
                 ["quest_recover_tome", "quest_slay_drake"],
                 ["the arcane", "the kingdom's history", "the void"],
                 ["He is slowly dying from a curse he absorbed to save the party."]),
                ("npc_merchant_gilda", "Gilda Goldcoin",
                 NPCRole.MERCHANT.value, AlignmentType.TRUE_NEUTRAL.value,
                 "Halfling", "Rogue",
                 ["shrewd", "cheerful", "opportunistic", "surprisingly generous"],
                 "A plump halfling woman with an ever-present smile and a wagon "
                 "full of curiosities from every corner of the realm.",
                 "Gilda travels the trade routes, selling goods and information "
                 "to anyone with coin. She has no allegiance but to profit, yet "
                 "she has been known to give free supplies to those in genuine need.",
                 20, "loc_market_district",
                 ["quest_deliver_goods"],
                 ["her wares", "the road", "rumors"],
                 ["She is a retired master thief who still has contacts in every guild."]),
                ("npc_captain_reyes", "Captain Elena Reyes",
                 NPCRole.ALLY.value, AlignmentType.NEUTRAL_GOOD.value,
                 "Human", "Fighter",
                 ["loyal", "tactical", "protective", "haunted by past failures"],
                 "A weathered woman in tactical gear with cybernetic eyes that "
                 "glow faint blue. She carries herself with military precision.",
                 "A former corporate security officer who defected after refusing "
                 "an order to fire on civilians. She now leads a small cell of "
                 "operatives fighting against corporate tyranny.",
                 50, "loc_safe_house",
                 ["quest_infiltrate_tower"],
                 ["the corporation", "her old unit", "the streets"],
                 ["She has a child being held hostage by the corporation."]),
                ("npc_thief_raven", "Raven",
                 NPCRole.RECURRING.value, AlignmentType.CHAOTIC_NEUTRAL.value,
                 "Half-Elf", "Rogue",
                 ["witty", "elusive", "selfish", "secretly soft-hearted"],
                 "A figure draped in dark cloaks with a mask depicting a raven. "
                 "Their movements are fluid and barely visible.",
                 "Raven is a master thief who has crossed the party's path many "
                 "times, sometimes as ally, sometimes as rival. Their true "
                 "identity and motives remain a mystery.",
                 10, "loc_underground",
                 ["quest_recover_gem"],
                 ["the heist", "the underground", "their identity"],
                 ["Raven is actually nobility, stealing to fund an orphanage."]),
                ("npc_quemada_boss", "Diego Quemada",
                 NPCRole.BOSS.value, AlignmentType.CHAOTIC_EVIL.value,
                 "Human", "Corporate Executive",
                 ["narcissistic", "brilliant", "sadistic", "charismatic"],
                 "A immaculately dressed man with gold-chrome cybernetics visible "
                 "beneath his skin. His smile never reaches his cold, calculating eyes.",
                 "Quemada clawed his way from the slums to the top of the Quemada "
                 "Corporation through sheer ruthlessness. He sees people as "
                 "resources to be expended.",
                 -90, "loc_quemada_tower",
                 ["quest_take_down_quemada"],
                 ["his empire", "the data shard", "his past"],
                 ["He is terminally ill and racing against time to achieve digital immortality."]),
                ("npc_henchman_grunt", "Grunt",
                 NPCRole.HENCHMAN.value, AlignmentType.NEUTRAL_EVIL.value,
                 "Orc", "Barbarian",
                 ["brutish", "loyal to whoever pays", "simple", "surprisingly honorable"],
                 "A massive, scar-covered orc with filed teeth and a collection "
                 "of trophies hanging from his belt. He carries a war-hammer.",
                 "Grunt has worked for every villain in the region at some point. "
                 "He follows orders without question but has a personal code "
                 "against harming children.",
                 -10, "loc_bandit_camp",
                 ["quest_defeat_grunt"],
                 ["his bosses", "the fighting life"],
                 ["He dreams of retiring to a farm, if he survives long enough."]),
                ("npc_quest_giver_farmer", "Old Farmer Bram",
                 NPCRole.QUEST_GIVER.value, AlignmentType.LAWFUL_GOOD.value,
                 "Human", "Commoner",
                 ["hardworking", "kind", "worried", "brave when it counts"],
                 "A weathered old man in patched overalls, hands rough from "
                 "decades of work. His eyes are tired but kind.",
                 "Bram has farmed the same land for forty years. When bandits "
                 "stole his livestock and kidnapped his granddaughter, he sought "
                 "out the party for help.",
                 30, "loc_bram_farm",
                 ["quest_rescue_granddaughter"],
                 ["his farm", "his granddaughter", "the bandits"],
                 ["He is a retired adventurer who hung up his sword for peace."]),
                ("npc_diplomat_vezra", "Ambassador Vezra",
                 NPCRole.NEUTRAL.value, AlignmentType.LAWFUL_NEUTRAL.value,
                 "Elf", "Aristocrat",
                 ["composed", "calculating", "fair", "emotionally distant"],
                 "An elf of regal bearing in immaculate diplomatic robes. Every "
                 "gesture is measured, every word carefully chosen.",
                 "Vezra represents the Elven Council in human affairs. She "
                 "maintains strict neutrality, balancing the interests of all "
                 "factions without taking sides.",
                 0, "loc_embassy",
                 ["quest_diplomatic_mission"],
                 ["the council", "the political landscape", "the treaties"],
                 ["She is secretly funding the rebellion to prevent a worse war."]),
                ("npc_background_innkeeper", "Martha Bright",
                 NPCRole.BACKGROUND.value, AlignmentType.NEUTRAL_GOOD.value,
                 "Human", "Commoner",
                 ["warm", "gossipy", "motherly", "observant"],
                 "A round, cheerful woman with flour-dusted hands and an apron "
                 "that has seen better days. She knows every regular by name.",
                 "Martha has run the Bright Lantern Inn for twenty years. She "
                 "knows every rumor that passes through her doors and is happy "
                 "to share them over a warm meal.",
                 15, "loc_bright_lantern",
                 [],
                 ["local gossip", "travelers", "her famous stew"],
                 ["She is the leader of an underground information network."]),
                ("npc_mystic_ora", "Ora the Mist-Walker",
                 NPCRole.MENTOR.value, AlignmentType.NEUTRAL_GOOD.value,
                 "Ethereal", "Mystic",
                 ["serene", "enigmatic", "compassionate", "otherworldly"],
                 "A translucent figure that seems to shimmer between existence "
                 "and void. Her voice echoes as if from a great distance.",
                 "Ora exists partially in the mortal world and partially in the "
                 "dream realm. She guides those who are lost, speaking in riddles "
                 "that only make sense in hindsight.",
                 40, "loc_dream_threshold",
                 ["quest_seek_ora"],
                 ["the dream realm", "the void", "destiny"],
                 ["She is slowly fading from existence and seeks someone to carry on her mission."]),
                ("npc_warlord_drax", "Warlord Drax the Devourer",
                 NPCRole.BOSS.value, AlignmentType.CHAOTIC_EVIL.value,
                 "Void-touched", "Warlord",
                 ["savage", "cunning", "immortal", "consuming"],
                 "A towering monstrosity of fused flesh and void-matter. It has "
                 "no single shape, shifting constantly as it devours all light nearby.",
                 "Drax was once a mortal explorer who touched the Void and was "
                 "remade. It now exists only to consume, growing stronger with "
                 "each soul it devours.",
                 -95, "loc_abyss_core",
                 ["quest_destroy_drax"],
                 ["the void", "its hunger", "its origin"],
                 ["A fragment of its mortal soul still fights against the void from within."]),
                ("npc_scientist_vale", "Dr. Marcus Vale",
                 NPCRole.ALLY.value, AlignmentType.LAWFUL_GOOD.value,
                 "Human", "Scientist",
                 ["brilliant", "anxious", "determined", "morally conflicted"],
                 "A thin man in a stained lab coat with a neural interface "
                 "embedded in his temple. His hands shake slightly when not working.",
                 "Dr. Vale was the lead researcher on the original expedition to "
                 "the derelict station. He knows more about the threat than anyone "
                 "but is haunted by what he helped create.",
                 55, "loc_research_lab",
                 ["quest_research_void"],
                 ["the research", "the station", "the void entities"],
                 ["He accidentally created the void breach that doomed the first expedition."]),
                ("npc_smuggler_jax", "Jax",
                 NPCRole.RECURRING.value, AlignmentType.CHAOTIC_NEUTRAL.value,
                 "Human", "Smuggler",
                 ["smooth-talking", "cunning", "loyal to friends", "always has a plan"],
                 "A wiry man with a cybernetic arm and a cocky grin. He dresses "
                 "in mismatched street clothes with hidden pockets everywhere.",
                 "Jax is the best smuggler in Neo-Veridia's underground. He can "
                 "get anything past any checkpoint, for the right price. He has "
                 "a soft spot for the party, though he'd never admit it.",
                 25, "loc_smuggler_den",
                 ["quest_smuggle_cargo"],
                 ["the underground", "his contacts", "the best routes"],
                 ["He is an undercover agent for an internal affairs division."]),
                ("npc_spirit_guide", "The Lantern Spirit",
                 NPCRole.MENTOR.value, AlignmentType.TRUE_NEUTRAL.value,
                 "Spirit", "Guide",
                 ["calm", "ancient", "impartial", "gentle"],
                 "A floating orb of soft golden light that pulses with a slow, "
                 "steady rhythm. When it speaks, the light flickers in patterns.",
                 "The Lantern Spirit has guided travelers through the darkest "
                 "places for millennia. It does not judge, it does not choose "
                 "sides, it only illuminates the path forward.",
                 35, "loc_dark_passage",
                 ["quest_follow_lantern"],
                 ["the darkness", "the paths", "the lost souls"],
                 ["It is bound to the station and cannot leave, even to save itself."]),
            ]
            for (npc_id, name, role, align, race, cls, traits,
                 appearance, backstory, rel, loc, quests, topics, secrets) in npc_specs:
                self._npcs[npc_id] = NPCProfile(
                    npc_id=npc_id, name=name, role=role, alignment=align,
                    race=race, class_name=cls, personality_traits=traits,
                    appearance=appearance, backstory=backstory,
                    relationship_level=rel, location_id=loc,
                    quest_ids=quests, dialogue_topics=topics, secrets=secrets,
                )

            # -- Moral Choices --------------------------------------------
            moral_specs = [
                ("moral_crown_hostage", "arc_crown_betrayal",
                 "The party discovers a hostage in the dungeon of Highreach: the "
                 "traitor's young sibling, who knows the location of the rebel base. "
                 "Do you free the innocent child, knowing they will reveal your "
                 "position to the enemy, or leave them to their fate to protect "
                 "the rebellion?",
                 MoralChoiceType.GOOD_VS_EVIL.value,
                 [
                     {"label": "Free the hostage", "description": "Save the innocent child, risking the rebellion's safety."},
                     {"label": "Leave the hostage", "description": "Protect the rebellion by leaving the child to suffer."},
                     {"label": "Take the hostage with you", "description": "Free the child and keep them close, hoping to control the information."},
                 ]),
                ("moral_neon_data", "arc_neon_conspiracy",
                 "The decrypted data shard proves that the Quemada Corporation "
                 "deliberately poisoned the water supply of a poor district to "
                 "test a new drug. Publishing the truth will cause riots and "
                 "innocent deaths, but burying it lets the corporation continue.",
                 MoralChoiceType.TRUTH_VS_LIES.value,
                 [
                     {"label": "Publish the truth", "description": "Expose the corporation, accepting the violent consequences."},
                     {"label": "Bury the data", "description": "Hide the truth to prevent chaos, letting the corporation continue."},
                     {"label": "Leak it anonymously", "description": "Release the data slowly through back channels to minimize fallout."},
                 ]),
                ("moral_void_sacrifice", "arc_void_abyss",
                 "The only path through the abyssal level requires someone to "
                 "stay behind and hold the door. The spirit guide offers to "
                 "remain, knowing it means permanent dissolution. Alternatively, "
                 "you could force the wounded henchman Grunt to stay, saving "
                 "both the spirit and yourselves.",
                 MoralChoiceType.SELF_VS_OTHERS.value,
                 [
                     {"label": "Accept the spirit's sacrifice", "description": "Let the spirit guide dissolve to save the party."},
                     {"label": "Force Grunt to stay", "description": "Sacrifice the henchman against his will to save everyone else."},
                     {"label": "Stay behind yourself", "description": "Sacrifice your own life so the party can escape."},
                 ]),
                ("moral_crown_mercy", "arc_crown_climax",
                 "King Aldric is defeated and at your mercy. He begs for his "
                 "life, revealing he has a daughter hidden away who would die "
                 "without his protection. Sparing him means he may rebuild his "
                 "tyranny, but killing him condemns an innocent child.",
                 MoralChoiceType.MERCY_VS_JUSTICE.value,
                 [
                     {"label": "Show mercy", "description": "Spare Aldric's life, risking future tyranny, to save his daughter."},
                     {"label": "Deliver justice", "description": "Execute Aldric for his crimes, accepting the daughter's fate."},
                     {"label": "Spare him conditionally", "description": "Let him live in exile, stripped of power, with his daughter."},
                 ]),
                ("moral_neon_loyalty", "arc_neon_revelation",
                 "Captain Reyes, your closest ally, is revealed to be working "
                 "with a rival corporation all along, though she insists she was "
                 "gathering intelligence to help the party. The data supports "
                 "both interpretations. Do you trust your friend or the evidence?",
                 MoralChoiceType.LAW_VS_CHAOS.value,
                 [
                     {"label": "Trust Reyes", "description": "Believe your ally's explanation and continue together."},
                     {"label": "Side with the evidence", "description": "Confront and detain Reyes based on the data."},
                     {"label": "Let her prove herself", "description": "Give Reyes a mission to prove her loyalty, under watch."},
                 ]),
            ]
            for choice_id, arc_id, desc, ctype, options in moral_specs:
                choice = MoralChoice(
                    choice_id=choice_id, arc_id=arc_id, description=desc,
                    choice_type=ctype, options=options,
                )
                self._moral_choices[choice_id] = choice
                if arc_id in self._story_arcs:
                    self._story_arcs[arc_id].moral_choices.append(choice_id)

            # -- Consequences ---------------------------------------------
            consequence_specs = [
                ("cons_crown_hostage_free", "moral_crown_hostage",
                 ConsequenceType.REPUTATION.value,
                 "The party is celebrated as heroes for freeing the hostage, "
                 "but the rebellion's position is compromised.",
                 ["npc_thief_raven", "npc_henchman_grunt"], 30, False),
                ("cons_crown_hostage_leave", "moral_crown_hostage",
                 ConsequenceType.RELATIONSHIP.value,
                 "The party's reputation suffers for abandoning the child, "
                 "but the rebellion remains safe.",
                 ["npc_thief_raven"], -20, False),
                ("cons_neon_data_publish", "moral_neon_data",
                 ConsequenceType.WORLD_STATE.value,
                 "The truth sparks violent uprisings across Neo-Veridia. The "
                 "corporation is weakened but the city burns.",
                 ["npc_quemada_boss", "npc_captain_reyes"], 50, True),
                ("cons_neon_data_bury", "moral_neon_data",
                 ConsequenceType.NARRATIVE.value,
                 "The corporation continues its experiments unchecked. The "
                 "party carries the weight of their silence.",
                 ["npc_captain_reyes"], -15, False),
                ("cons_void_sacrifice_spirit", "moral_void_sacrifice",
                 ConsequenceType.ITEM_LOSS.value,
                 "The spirit guide dissolves holding the door. Its lantern "
                 "remains, a permanent but bittersweet gift.",
                 ["npc_spirit_guide"], 40, True),
                ("cons_void_sacrifice_grunt", "moral_void_sacrifice",
                 ConsequenceType.RELATIONSHIP.value,
                 "Grunt is forced to stay behind. His screams echo as the party "
                 "escapes, haunting them forever.",
                 ["npc_henchman_grunt"], -50, True),
                ("cons_crown_mercy_spare", "moral_crown_mercy",
                 ConsequenceType.REPUTATION.value,
                 "Aldric is spared and exiled. The kingdom questions the party's "
                 "judgment, but the daughter is saved.",
                 ["npc_king_aldric"], 10, True),
                ("cons_crown_mercy_justice", "moral_crown_mercy",
                 ConsequenceType.MECHANICAL.value,
                 "Aldric is executed. The party gains closure but the daughter's "
                 "fate remains unknown.",
                 ["npc_king_aldric"], 25, True),
                ("cons_neon_loyalty_trust", "moral_neon_loyalty",
                 ConsequenceType.RELATIONSHIP.value,
                 "Reyes proves her loyalty was genuine. The party's bond grows "
                 "stronger through the trial of trust.",
                 ["npc_captain_reyes"], 35, False),
                ("cons_neon_loyalty_evidence", "moral_neon_loyalty",
                 ConsequenceType.NARRATIVE.value,
                 "Reyes is detained based on the evidence. If she was innocent, "
                 "the party has lost a valuable ally at a critical moment.",
                 ["npc_captain_reyes"], -25, False),
            ]
            for cons_id, choice_id, ctype, desc, entities, magnitude, permanent in consequence_specs:
                cons = Consequence(
                    consequence_id=cons_id, choice_id=choice_id, type=ctype,
                    description=desc, affected_entities=entities,
                    magnitude=magnitude, is_permanent=permanent,
                )
                self._consequences[cons_id] = cons
                if choice_id in self._moral_choices:
                    self._moral_choices[choice_id].consequences.append(cons_id)

            # -- Encounters -----------------------------------------------
            encounter_specs = [
                ("enc_crown_ambush", crown, EncounterDifficulty.MEDIUM.value,
                 "A band of King Aldric's loyalists ambushes the party on the "
                 "road to Highreach Keep, emerging from the treeline with "
                 "crossbows drawn.",
                 ["npc_henchman_grunt"], "loc_highreach_road", 300,
                 ["potion_of_healing", "silver_dagger"],
                 "Triggered when the party travels to Highreach Keep."),
                ("enc_crown_throne_room", crown, EncounterDifficulty.BOSS.value,
                 "The throne room of Aethelgard. King Aldric stands atop the "
                 "dais, surrounded by his royal guard, the crown of black iron "
                 "glowing with dark power.",
                 ["npc_king_aldric"], "loc_throne_room", 1500,
                 ["crown_shard", "royal_pendant", "ancient_tome"],
                 "Triggered when the party enters the throne room."),
                ("enc_neon_rooftop", neon, EncounterDifficulty.HARD.value,
                 "A rooftop chase across the neon-lit skyline of Neo-Veridia. "
                 "Corporate enforcers pursue the party across rain-slicked "
                 "rooftops with gunfire and drones.",
                 ["npc_smuggler_jax"], "loc_rooftop_chase", 500,
                 ["credit_chip", "stim_pack", "drone_parts"],
                 "Triggered after the data shard is decrypted."),
                ("enc_neon_lab_raid", neon, EncounterDifficulty.MEDIUM.value,
                 "A raid on the corporate lab where the data shard was created. "
                 "Security drones and armed guards patrol the sterile corridors.",
                 ["npc_henchman_grunt"], "loc_corporate_lab", 400,
                 ["data_shard", "encryption_key", "med_kit"],
                 "Triggered when the party infiltrates the lab."),
                ("enc_void_first_contact", void, EncounterDifficulty.DEADLY.value,
                 "First contact with the void entities in the upper decks. "
                 "The lights flicker and die as something massive moves in the "
                 "darkness between the corridors.",
                 ["npc_warlord_drax"], "loc_upper_decks", 800,
                 ["void_crystal", "ancient_relic"],
                 "Triggered when the party explores the upper decks alone."),
                ("enc_void_abyss_horror", void, EncounterDifficulty.DEADLY.value,
                 "The abyssal horror emerges from the walls of the deepest "
                 "level, a writhing mass of void-matter and fused souls that "
                 "fills the corridor with existential dread.",
                 ["npc_warlord_drax"], "loc_abyssal_level", 1200,
                 ["void_essence", "abyssal_core", "lantern_fragment"],
                 "Triggered when the party descends to the abyssal level."),
                ("enc_crown_bandit_camp", crown, EncounterDifficulty.EASY.value,
                 "A small bandit camp in the woods near Bram's farm. The "
                 "bandits are poorly armed but numerous, camped around a fire.",
                 ["npc_henchman_grunt"], "loc_bandit_camp", 100,
                 ["stolen_goods", "provisions"],
                 "Triggered when the party investigates the bandit camp."),
                ("enc_neon_street_fight", neon, EncounterDifficulty.EASY.value,
                 "A street brawl in the lower levels of Neo-Veridia. Rival gang "
                 "members challenge the party's claim to the territory, fists "
                 "and improvised weapons flying.",
                 ["npc_henchman_grunt"], "loc_lower_streets", 80,
                 ["street_cred", "cheap_weapon"],
                 "Triggered when the party enters rival gang territory."),
            ]
            for enc_id, camp, diff, desc, enemies, loc, xp, items, trigger in encounter_specs:
                self._encounters[enc_id] = Encounter(
                    encounter_id=enc_id, campaign_id=camp, difficulty=diff,
                    description=desc, enemy_ids=enemies, location_id=loc,
                    reward_xp=xp, reward_items=items, trigger_condition=trigger,
                )

            # -- Party Members --------------------------------------------
            party_specs = [
                ("party_knight_lyra", "player_1", crown,
                 "Lyra Ashbound", "Human", "Paladin", 5,
                 PartyRole.TANK.value, AlignmentType.LAWFUL_GOOD.value,
                 "A knight sworn to protect the innocent, Lyra carries the "
                 "weight of a failed oath. She fights with shield and faith.",
                 45, 45,
                 {"strength": 16, "dexterity": 10, "constitution": 15,
                  "intelligence": 10, "wisdom": 13, "charisma": 14},
                 ["shield_of_aethelgard", "longsword", "holy_symbol"]),
                ("party_rogue_finn", "player_2", crown,
                 "Finn Nightwhisper", "Half-Elf", "Rogue", 5,
                 PartyRole.SCOUT.value, AlignmentType.CHAOTIC_GOOD.value,
                 "A street thief with a heart of gold, Finn grew up in the "
                 "alleys of the capital. He picks locks and pockets with "
                 "equal ease, but never steals from those who cannot afford it.",
                 28, 28,
                 {"strength": 10, "dexterity": 18, "constitution": 12,
                  "intelligence": 14, "wisdom": 12, "charisma": 13},
                 ["daggers", "thieves_tools", "cloak_of_shadows"]),
                ("party_mage_zara", "player_3", crown,
                 "Zara Stormcaller", "Human", "Wizard", 5,
                 PartyRole.DAMAGE_DEALER.value, AlignmentType.NEUTRAL_GOOD.value,
                 "A prodigy of the arcane academy, Zara wields destructive "
                 "magic with terrifying precision. She seeks the lost tomes "
                 "of the first archmages.",
                 22, 22,
                 {"strength": 8, "dexterity": 12, "constitution": 10,
                  "intelligence": 19, "wisdom": 15, "charisma": 11},
                 ["staff_of_storms", "spellbook", "arcane_focus"]),
                ("party_cleric_thom", "player_4", crown,
                 "Thom Brightblade", "Dwarf", "Cleric", 5,
                 PartyRole.HEALER.value, AlignmentType.LAWFUL_GOOD.value,
                 "A devout cleric of the forge god, Thom heals the wounded "
                 "and smites the undead with equal fervor. His faith is "
                 "unshakeable, even in the darkest dungeons.",
                 30, 30,
                 {"strength": 14, "dexterity": 10, "constitution": 16,
                  "intelligence": 11, "wisdom": 17, "charisma": 12},
                 ["warhammer", "holy_symbol", "shield_of_faith"]),
                ("party_ranger_vex", "player_5", void,
                 "Vex Longshot", "Elf", "Ranger", 5,
                 PartyRole.STRATEGIST.value, AlignmentType.CHAOTIC_GOOD.value,
                 "An elite marksman trained in zero-G combat, Vex was part "
                 "of the original survey team. She knows the station's "
                 "layout better than anyone alive.",
                 30, 30,
                 {"strength": 12, "dexterity": 17, "constitution": 13,
                  "intelligence": 14, "wisdom": 16, "charisma": 10},
                 ["plasma_rifle", "survival_kit", "motion_scanner"]),
                ("party_bard_aria", "player_6", neon,
                 "Aria Songweaver", "Half-Elf", "Bard", 5,
                 PartyRole.DIPLOMAT.value, AlignmentType.CHAOTIC_GOOD.value,
                 "A street performer turned revolutionary, Aria uses music "
                 "and words as weapons. She can talk her way into or out "
                 "of almost any situation.",
                 26, 26,
                 {"strength": 9, "dexterity": 14, "constitution": 12,
                  "intelligence": 13, "wisdom": 12, "charisma": 18},
                 ["electric_lute", "datasynth", "charm_bracelet"]),
            ]
            for (mid, pid, camp, cname, race, cls, lvl, role, align,
                 story, hp, maxhp, stats, inv) in party_specs:
                self._parties[mid] = PartyMember(
                    member_id=mid, player_id=pid, campaign_id=camp,
                    character_name=cname, race=race, class_name=cls,
                    level=lvl, party_role=role, alignment=align,
                    backstory=story, current_hp=hp, max_hp=maxhp,
                    stats=stats, inventory=inv,
                )
                if camp in self._campaigns:
                    self._campaigns[camp].player_ids.append(pid)

            # -- World States ---------------------------------------------
            self._world_states[crown] = WorldState(
                state_id="ws_shattered_crown", campaign_id=crown,
                faction_power={"Crown": 75, "Rebellion": 35, "Church": 60, "Merchants Guild": 50},
                location_states={"Throne Room": "contested", "Highreach Keep": "rebel_held",
                                 "Market District": "crown_controlled", "Sage Tower": "neutral"},
                global_flags={"king_aldric_warned": False, "rebellion_discovered": True,
                              "daughter_found": False, "tome_recovered": False},
                time_elapsed=12.5, day_count=3, weather="overcast", season="autumn",
            )
            self._world_states[neon] = WorldState(
                state_id="ws_neon_shadows", campaign_id=neon,
                faction_power={"Quemada Corp": 85, "Underground": 40, "City Police": 55, "Hackers Collective": 30},
                location_states={"Quemada Tower": "corporate_held", "Rooftop Bar": "neutral",
                                 "Server Farm": "contested", "Lower Streets": "gang_territory"},
                global_flags={"data_shard_decrypted": True, "reyes_trust_tested": False,
                              "riot_started": False, "quemada_exposed": False},
                time_elapsed=8.0, day_count=2, weather="rain", season="summer",
            )
            self._world_states[void] = WorldState(
                state_id="ws_void_expedition", campaign_id=void,
                faction_power={"Expedition Crew": 40, "Void Entities": 80, "Station AI": 55, "Ancient Remnants": 25},
                location_states={"Upper Decks": "explored", "Base Camp": "secured",
                                 "Abyssal Level": "unexplored", "Escape Bay": "locked"},
                global_flags={"base_camp_established": True, "signal_investigated": True,
                              "spirit_met": True, "abyss_entered": False},
                time_elapsed=4.5, day_count=1, weather="void_storm", season="unknown",
            )

            # -- Stats ----------------------------------------------------
            self._stats.total_campaigns = len(self._campaigns)
            self._stats.active_campaigns = sum(
                1 for c in self._campaigns.values()
                if c.status == CampaignStatus.ACTIVE.value
            )
            self._stats.total_npcs = len(self._npcs)
            self._stats.total_encounters = len(self._encounters)
            self._stats.moral_choices_made = sum(
                1 for m in self._moral_choices.values() if m.is_resolved
            )
            self._stats.sessions_run = 6
            self._stats.avg_session_length = 3.5
            self._stats.total_events = 0

            self._initialized = True

    def _emit(self, kind: str, campaign_id: str = "", session_id: str = "",
              **data: Any) -> None:
        self._event_counter += 1
        event = DungeonMasterEvent(
            event_id=f"dmevt_{self._event_counter:08d}",
            kind=kind, timestamp=_now(),
            campaign_id=campaign_id, session_id=session_id,
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        self._stats.total_events = len(self._events)

    # ------------------------------------------------------------------
    # Campaign Management
    # ------------------------------------------------------------------

    def register_campaign(
        self, campaign_id: str, name: str, campaign_type: str,
        description: str = "", dm_style: str = "balanced", setting: str = "",
        tone: str = "heroic", starting_level: int = 1, max_players: int = 6,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Campaign]]:
        with _lock:
            if campaign_id in self._campaigns:
                return False, "already_exists", None
            if len(self._campaigns) >= self._config.max_campaigns:
                return False, "capacity_reached", None
            campaign = Campaign(
                campaign_id=campaign_id, name=name, type=campaign_type,
                description=description, dm_style=dm_style, setting=setting,
                tone=tone, starting_level=max(1, starting_level),
                max_players=max(1, max_players),
                status=CampaignStatus.PREPARING.value,
                metadata=metadata or {},
            )
            self._campaigns[campaign_id] = campaign
            self._stats.total_campaigns = len(self._campaigns)
            self._emit(DungeonMasterEventKind.CAMPAIGN_STARTED.value,
                       campaign_id=campaign_id, name=name)
            return True, "registered", campaign

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        return self._campaigns.get(campaign_id)

    def list_campaigns(self, status: str = "") -> List[Campaign]:
        results = list(self._campaigns.values())
        if status:
            results = [c for c in results if c.status == status]
        return results

    def remove_campaign(self, campaign_id: str) -> Tuple[bool, str]:
        with _lock:
            if campaign_id not in self._campaigns:
                return False, "not_found"
            campaign = self._campaigns.pop(campaign_id)
            # Cascade: remove story arcs for this campaign
            for arc_id in campaign.story_arcs:
                arc = self._story_arcs.pop(arc_id, None)
                if arc:
                    for cid in arc.moral_choices:
                        choice = self._moral_choices.pop(cid, None)
                        if choice:
                            for cons_id in choice.consequences:
                                self._consequences.pop(cons_id, None)
            # Remove encounters for this campaign
            to_remove = [eid for eid, e in self._encounters.items()
                         if e.campaign_id == campaign_id]
            for eid in to_remove:
                self._encounters.pop(eid, None)
            # Remove party members for this campaign
            to_remove_p = [mid for mid, p in self._parties.items()
                           if p.campaign_id == campaign_id]
            for mid in to_remove_p:
                self._parties.pop(mid, None)
            # Remove world state
            self._world_states.pop(campaign_id, None)
            self._stats.total_campaigns = len(self._campaigns)
            self._stats.active_campaigns = sum(
                1 for c in self._campaigns.values()
                if c.status == CampaignStatus.ACTIVE.value
            )
            self._emit("campaign_removed", campaign_id=campaign_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # Story Arc Management
    # ------------------------------------------------------------------

    def register_story_arc(
        self, arc_id: str, campaign_id: str, arc_type: str, title: str,
        description: str = "", objectives: Optional[List[str]] = None,
        key_npcs: Optional[List[str]] = None,
        key_locations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[StoryArc]]:
        with _lock:
            if arc_id in self._story_arcs:
                return False, "already_exists", None
            if campaign_id not in self._campaigns:
                return False, "campaign_not_found", None
            if len(self._story_arcs) >= _MAX_STORY_ARCS:
                return False, "capacity_reached", None
            arc = StoryArc(
                arc_id=arc_id, campaign_id=campaign_id, arc_type=arc_type,
                title=title, description=description,
                objectives=objectives or [], key_npcs=key_npcs or [],
                key_locations=key_locations or [], metadata=metadata or {},
            )
            self._story_arcs[arc_id] = arc
            self._campaigns[campaign_id].story_arcs.append(arc_id)
            self._emit(DungeonMasterEventKind.STORY_BEAT.value,
                       campaign_id=campaign_id, arc_id=arc_id, title=title)
            return True, "registered", arc

    def get_story_arc(self, arc_id: str) -> Optional[StoryArc]:
        return self._story_arcs.get(arc_id)

    def list_story_arcs(self, campaign_id: str = "") -> List[StoryArc]:
        results = list(self._story_arcs.values())
        if campaign_id:
            results = [a for a in results if a.campaign_id == campaign_id]
        return results

    def remove_story_arc(self, arc_id: str) -> Tuple[bool, str]:
        with _lock:
            arc = self._story_arcs.get(arc_id)
            if not arc:
                return False, "not_found"
            self._story_arcs.pop(arc_id, None)
            campaign = self._campaigns.get(arc.campaign_id)
            if campaign:
                if arc_id in campaign.story_arcs:
                    campaign.story_arcs.remove(arc_id)
                if campaign.current_arc == arc_id:
                    campaign.current_arc = ""
            # Cascade: remove moral choices and consequences for this arc
            for cid in list(arc.moral_choices):
                choice = self._moral_choices.pop(cid, None)
                if choice:
                    for cons_id in choice.consequences:
                        self._consequences.pop(cons_id, None)
            self._emit("story_arc_removed", campaign_id=arc.campaign_id,
                       arc_id=arc_id)
            return True, "removed"

    def advance_story_arc(self, arc_id: str) -> Tuple[bool, str, Optional[StoryArc]]:
        with _lock:
            arc = self._story_arcs.get(arc_id)
            if not arc:
                return False, "not_found", None
            if arc.is_resolved:
                return False, "already_resolved", arc

            transitions = {
                StoryArcType.INTRODUCTION.value: StoryArcType.RISING_ACTION,
                StoryArcType.RISING_ACTION.value: StoryArcType.CLIMAX,
                StoryArcType.CLIMAX.value: StoryArcType.FALLING_ACTION,
                StoryArcType.FALLING_ACTION.value: StoryArcType.RESOLUTION,
                StoryArcType.SIDE_QUEST.value: StoryArcType.RESOLUTION,
                StoryArcType.INTERLUDE.value: StoryArcType.RISING_ACTION,
            }
            new_type = transitions.get(arc.arc_type)
            if not new_type:
                return False, "no_transition", arc

            arc.arc_type = new_type.value
            if new_type == StoryArcType.RESOLUTION:
                arc.is_resolved = True
                arc.resolution = arc.resolution or f"Arc '{arc.title}' has reached its resolution."
                campaign = self._campaigns.get(arc.campaign_id)
                if campaign and campaign.current_arc == arc_id:
                    # Move to next unresolved arc in the campaign
                    for next_arc_id in campaign.story_arcs:
                        next_arc = self._story_arcs.get(next_arc_id)
                        if next_arc and not next_arc.is_resolved:
                            campaign.current_arc = next_arc_id
                            break
                    else:
                        campaign.current_arc = ""

            self._emit(DungeonMasterEventKind.STORY_BEAT.value,
                       campaign_id=arc.campaign_id, arc_id=arc_id,
                       new_type=new_type.value, title=arc.title)
            return True, "advanced", arc

    # ------------------------------------------------------------------
    # NPC Management
    # ------------------------------------------------------------------

    def register_npc(
        self, npc_id: str, name: str, role: str, alignment: str,
        race: str = "", class_name: str = "",
        personality_traits: Optional[List[str]] = None,
        appearance: str = "", backstory: str = "",
        location_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[NPCProfile]]:
        with _lock:
            if npc_id in self._npcs:
                return False, "already_exists", None
            if len(self._npcs) >= _MAX_NPCS:
                return False, "capacity_reached", None
            npc = NPCProfile(
                npc_id=npc_id, name=name, role=role, alignment=alignment,
                race=race, class_name=class_name,
                personality_traits=personality_traits or [],
                appearance=appearance, backstory=backstory,
                location_id=location_id, metadata=metadata or {},
            )
            self._npcs[npc_id] = npc
            self._stats.total_npcs = len(self._npcs)
            self._emit(DungeonMasterEventKind.NPC_INTRODUCED.value,
                       npc_id=npc_id, name=name, role=role)
            return True, "registered", npc

    def get_npc(self, npc_id: str) -> Optional[NPCProfile]:
        return self._npcs.get(npc_id)

    def list_npcs(self, campaign_id: str = "", role: str = "") -> List[NPCProfile]:
        results = list(self._npcs.values())
        if campaign_id:
            # Find NPCs linked to this campaign via story arcs and encounters
            linked_ids: set = set()
            for arc in self._story_arcs.values():
                if arc.campaign_id == campaign_id:
                    linked_ids.update(arc.key_npcs)
            for enc in self._encounters.values():
                if enc.campaign_id == campaign_id:
                    linked_ids.update(enc.enemy_ids)
            results = [n for n in results if n.npc_id in linked_ids]
        if role:
            results = [n for n in results if n.role == role]
        return results

    def remove_npc(self, npc_id: str) -> Tuple[bool, str]:
        with _lock:
            if npc_id not in self._npcs:
                return False, "not_found"
            self._npcs.pop(npc_id, None)
            self._stats.total_npcs = len(self._npcs)
            self._emit("npc_removed", npc_id=npc_id)
            return True, "removed"

    def set_npc_relationship(self, npc_id: str, level: int) -> Tuple[bool, str, Optional[NPCProfile]]:
        with _lock:
            npc = self._npcs.get(npc_id)
            if not npc:
                return False, "not_found", None
            npc.relationship_level = int(_clamp(level, -100, 100))
            self._emit("npc_relationship_changed", npc_id=npc_id,
                       new_level=npc.relationship_level)
            return True, "updated", npc

    # ------------------------------------------------------------------
    # Moral Choice Management
    # ------------------------------------------------------------------

    def register_moral_choice(
        self, choice_id: str, arc_id: str, description: str,
        choice_type: str, options: Optional[List[Dict[str, Any]]] = None,
        consequences: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MoralChoice]]:
        with _lock:
            if choice_id in self._moral_choices:
                return False, "already_exists", None
            if arc_id not in self._story_arcs:
                return False, "arc_not_found", None
            if len(self._moral_choices) >= _MAX_MORAL_CHOICES:
                return False, "capacity_reached", None
            choice = MoralChoice(
                choice_id=choice_id, arc_id=arc_id, description=description,
                choice_type=choice_type, options=options or [],
                consequences=consequences or [], metadata=metadata or {},
            )
            self._moral_choices[choice_id] = choice
            self._story_arcs[arc_id].moral_choices.append(choice_id)
            self._emit(DungeonMasterEventKind.MORAL_CHOICE.value,
                       arc_id=arc_id, choice_id=choice_id,
                       choice_type=choice_type)
            return True, "registered", choice

    def get_moral_choice(self, choice_id: str) -> Optional[MoralChoice]:
        return self._moral_choices.get(choice_id)

    def list_moral_choices(self, arc_id: str = "") -> List[MoralChoice]:
        results = list(self._moral_choices.values())
        if arc_id:
            results = [m for m in results if m.arc_id == arc_id]
        return results

    def resolve_moral_choice(self, choice_id: str, player_choice: str) -> Tuple[bool, str, Optional[MoralChoice]]:
        with _lock:
            choice = self._moral_choices.get(choice_id)
            if not choice:
                return False, "not_found", None
            if choice.is_resolved:
                return False, "already_resolved", choice
            # Validate that player_choice corresponds to an option
            valid_labels = [opt.get("label", "") for opt in choice.options]
            if choice.options and player_choice not in valid_labels:
                return False, "invalid_choice", choice
            choice.player_choice = player_choice
            choice.is_resolved = True
            self._stats.moral_choices_made += 1
            self._emit(DungeonMasterEventKind.MORAL_CHOICE.value,
                       arc_id=choice.arc_id, choice_id=choice_id,
                       player_choice=player_choice, resolved=True)
            return True, "resolved", choice

    def apply_consequence(self, consequence_id: str) -> Tuple[bool, str, Optional[Consequence]]:
        with _lock:
            cons = self._consequences.get(consequence_id)
            if not cons:
                return False, "not_found", None
            if consequence_id in self._applied_consequences:
                return False, "already_applied", cons
            self._applied_consequences.add(consequence_id)
            # Apply magnitude effects to affected NPC relationships
            for entity_id in cons.affected_entities:
                npc = self._npcs.get(entity_id)
                if npc:
                    npc.relationship_level = int(_clamp(
                        npc.relationship_level + cons.magnitude, -100, 100))
            # Apply world state changes if applicable
            choice = self._moral_choices.get(cons.choice_id)
            if choice:
                arc = self._story_arcs.get(choice.arc_id)
                if arc:
                    ws = self._world_states.get(arc.campaign_id)
                    if ws:
                        ws.global_flags[f"consequence_{consequence_id}"] = True
            self._emit(DungeonMasterEventKind.CONSEQUENCE_APPLIED.value,
                       campaign_id=arc.campaign_id if choice and arc else "",
                       consequence_id=consequence_id,
                       consequence_type=cons.type,
                       magnitude=cons.magnitude,
                       is_permanent=cons.is_permanent)
            return True, "applied", cons

    # ------------------------------------------------------------------
    # Encounter Management
    # ------------------------------------------------------------------

    def register_encounter(
        self, encounter_id: str, campaign_id: str, difficulty: str,
        description: str = "", enemy_ids: Optional[List[str]] = None,
        location_id: str = "", reward_xp: int = 0,
        reward_items: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Encounter]]:
        with _lock:
            if encounter_id in self._encounters:
                return False, "already_exists", None
            if campaign_id not in self._campaigns:
                return False, "campaign_not_found", None
            if len(self._encounters) >= _MAX_ENCOUNTERS:
                return False, "capacity_reached", None
            encounter = Encounter(
                encounter_id=encounter_id, campaign_id=campaign_id,
                difficulty=difficulty, description=description,
                enemy_ids=enemy_ids or [], location_id=location_id,
                reward_xp=max(0, reward_xp), reward_items=reward_items or [],
                metadata=metadata or {},
            )
            self._encounters[encounter_id] = encounter
            self._stats.total_encounters = len(self._encounters)
            self._emit(DungeonMasterEventKind.ENCOUNTER_TRIGGERED.value,
                       campaign_id=campaign_id, encounter_id=encounter_id,
                       difficulty=difficulty)
            return True, "registered", encounter

    def get_encounter(self, encounter_id: str) -> Optional[Encounter]:
        return self._encounters.get(encounter_id)

    def list_encounters(self, campaign_id: str = "", difficulty: str = "") -> List[Encounter]:
        results = list(self._encounters.values())
        if campaign_id:
            results = [e for e in results if e.campaign_id == campaign_id]
        if difficulty:
            results = [e for e in results if e.difficulty == difficulty]
        return results

    def complete_encounter(self, encounter_id: str) -> Tuple[bool, str, Optional[Encounter]]:
        with _lock:
            encounter = self._encounters.get(encounter_id)
            if not encounter:
                return False, "not_found", None
            if encounter.is_completed:
                return False, "already_completed", encounter
            encounter.is_completed = True
            # Award XP to party members in the campaign
            party = [p for p in self._parties.values()
                     if p.campaign_id == encounter.campaign_id]
            for member in party:
                current_xp = _safe_int(member.stats.get("xp", 0), 0)
                member.stats["xp"] = current_xp + encounter.reward_xp
            # Distribute items round-robin among party members
            for idx, item in enumerate(encounter.reward_items):
                if party:
                    target = party[idx % len(party)]
                    target.inventory.append(item)
            self._emit(DungeonMasterEventKind.PLAYER_ACTION.value,
                       campaign_id=encounter.campaign_id,
                       encounter_id=encounter_id,
                       reward_xp=encounter.reward_xp,
                       reward_items=encounter.reward_items)
            return True, "completed", encounter

    def scale_encounter(self, encounter_id: str, party_level: int,
                        party_size: int) -> Optional[Encounter]:
        with _lock:
            encounter = self._encounters.get(encounter_id)
            if not encounter:
                return None
            # Scale reward XP based on party level and size
            base_xp = encounter.reward_xp
            level_factor = max(0.5, party_level / 5.0)
            size_factor = max(0.5, party_size / 4.0)
            encounter.reward_xp = int(base_xp * level_factor * size_factor)
            # Scale difficulty if auto-balance is enabled
            if self._config.auto_balance_encounters:
                new_difficulty = self.calculate_encounter_difficulty(
                    party_level, party_size, base_xp / 100.0)
                if new_difficulty:
                    encounter.difficulty = new_difficulty
            self._emit("encounter_scaled",
                       campaign_id=encounter.campaign_id,
                       encounter_id=encounter_id,
                       new_xp=encounter.reward_xp,
                       new_difficulty=encounter.difficulty)
            return encounter

    # ------------------------------------------------------------------
    # Party Member Management
    # ------------------------------------------------------------------

    def register_party_member(
        self, member_id: str, player_id: str, campaign_id: str,
        character_name: str, race: str, class_name: str, level: int = 1,
        party_role: str = PartyRole.UTILITY.value,
        alignment: str = AlignmentType.TRUE_NEUTRAL.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PartyMember]]:
        with _lock:
            if member_id in self._parties:
                return False, "already_exists", None
            if campaign_id not in self._campaigns:
                return False, "campaign_not_found", None
            if len(self._parties) >= _MAX_PARTY_MEMBERS:
                return False, "capacity_reached", None
            # Check party size limit
            current_party_size = sum(
                1 for p in self._parties.values()
                if p.campaign_id == campaign_id)
            if current_party_size >= self._config.max_party_size:
                return False, "party_full", None
            member = PartyMember(
                member_id=member_id, player_id=player_id,
                campaign_id=campaign_id, character_name=character_name,
                race=race, class_name=class_name, level=max(1, level),
                party_role=party_role, alignment=alignment,
                metadata=metadata or {},
            )
            self._parties[member_id] = member
            self._campaigns[campaign_id].player_ids.append(player_id)
            self._emit(DungeonMasterEventKind.PLAYER_ACTION.value,
                       campaign_id=campaign_id, member_id=member_id,
                       character_name=character_name)
            return True, "registered", member

    def get_party_member(self, member_id: str) -> Optional[PartyMember]:
        return self._parties.get(member_id)

    def list_party_members(self, campaign_id: str = "") -> List[PartyMember]:
        results = list(self._parties.values())
        if campaign_id:
            results = [p for p in results if p.campaign_id == campaign_id]
        return results

    def remove_party_member(self, member_id: str) -> Tuple[bool, str]:
        with _lock:
            member = self._parties.get(member_id)
            if not member:
                return False, "not_found"
            self._parties.pop(member_id, None)
            campaign = self._campaigns.get(member.campaign_id)
            if campaign and member.player_id in campaign.player_ids:
                campaign.player_ids.remove(member.player_id)
            self._emit("party_member_removed",
                       campaign_id=member.campaign_id, member_id=member_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # World State Management
    # ------------------------------------------------------------------

    def get_world_state(self, campaign_id: str) -> Optional[WorldState]:
        return self._world_states.get(campaign_id)

    def update_world_state(self, campaign_id: str,
                           updates: Dict[str, Any]) -> Tuple[bool, str, Optional[WorldState]]:
        with _lock:
            ws = self._world_states.get(campaign_id)
            if not ws:
                return False, "not_found", None
            # Merge faction_power dict
            if "faction_power" in updates and isinstance(updates["faction_power"], dict):
                for faction, power in updates["faction_power"].items():
                    current = ws.faction_power.get(faction, 0)
                    ws.faction_power[faction] = current + _safe_int(power, 0)
            # Merge location_states dict
            if "location_states" in updates and isinstance(updates["location_states"], dict):
                ws.location_states.update(updates["location_states"])
            # Merge global_flags dict
            if "global_flags" in updates and isinstance(updates["global_flags"], dict):
                ws.global_flags.update(updates["global_flags"])
            # Advance time
            if "time_elapsed" in updates:
                ws.time_elapsed += _safe_float(updates["time_elapsed"], 0.0)
                # Roll over to new day if time exceeds 24 hours
                while ws.time_elapsed >= 24.0:
                    ws.time_elapsed -= 24.0
                    ws.day_count += 1
            if "day_count" in updates:
                ws.day_count += _safe_int(updates["day_count"], 0)
            if "weather" in updates:
                ws.weather = str(updates["weather"])
            if "season" in updates:
                ws.season = str(updates["season"])
            self._emit("world_state_updated", campaign_id=campaign_id,
                       day_count=ws.day_count, weather=ws.weather)
            return True, "updated", ws

    # ------------------------------------------------------------------
    # Narrative, Rules, and Difficulty
    # ------------------------------------------------------------------

    def generate_narrative(self, campaign_id: str, context: str = "") -> Optional[str]:
        """Compose a narrative summary from the campaign's current state."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None
        arcs = [a for a in self._story_arcs.values() if a.campaign_id == campaign_id]
        world_state = self._world_states.get(campaign_id)

        parts: List[str] = []
        parts.append(f"=== {campaign.name} ===")
        parts.append(f"Type: {campaign.type.replace('_', ' ').title()}")
        parts.append(f"Setting: {campaign.setting}")
        parts.append(f"Tone: {campaign.tone}")
        parts.append(f"DM Style: {campaign.dm_style}")
        parts.append("")

        if campaign.description:
            parts.append(campaign.description)
            parts.append("")

        if context:
            parts.append(f"Context: {context}")
            parts.append("")

        # Current arc details
        if campaign.current_arc:
            arc = self._story_arcs.get(campaign.current_arc)
            if arc:
                parts.append(f"Current Arc: {arc.title}")
                parts.append(f"  Phase: {arc.arc_type.replace('_', ' ').title()}")
                if arc.description:
                    parts.append(f"  {arc.description}")
                if arc.objectives:
                    parts.append("  Objectives:")
                    for obj in arc.objectives:
                        parts.append(f"    - {obj}")
                if arc.key_locations:
                    parts.append(f"  Key Locations: {', '.join(arc.key_locations)}")
                parts.append("")

        # Story arcs overview
        if arcs:
            parts.append(f"Story Arcs ({len(arcs)}):")
            for arc in arcs:
                status = "resolved" if arc.is_resolved else "active"
                parts.append(f"  [{status}] {arc.title} ({arc.arc_type})")
            parts.append("")

        # Key NPCs
        npc_ids: set = set()
        for arc in arcs:
            npc_ids.update(arc.key_npcs)
        npcs = [self._npcs[nid] for nid in npc_ids if nid in self._npcs]
        if npcs:
            parts.append(f"Key NPCs ({len(npcs)}):")
            for npc in npcs[:6]:
                parts.append(f"  - {npc.name} ({npc.role}, {npc.alignment})")
                if npc.appearance:
                    parts.append(f"    {npc.appearance}")
            parts.append("")

        # World state
        if world_state:
            parts.append("World State:")
            parts.append(f"  Day: {world_state.day_count}, "
                         f"Time: {world_state.time_elapsed:.1f}h")
            parts.append(f"  Weather: {world_state.weather}, "
                         f"Season: {world_state.season}")
            if world_state.faction_power:
                parts.append("  Factions:")
                for faction, power in list(world_state.faction_power.items())[:4]:
                    parts.append(f"    {faction}: {power}")
            parts.append("")

        # Party
        party = [p for p in self._parties.values() if p.campaign_id == campaign_id]
        if party:
            parts.append(f"Party ({len(party)} members):")
            for member in party:
                parts.append(f"  - {member.character_name} (Lv.{member.level} "
                             f"{member.race} {member.class_name}, {member.party_role})")
                parts.append(f"    HP: {member.current_hp}/{member.max_hp}")
            parts.append("")

        parts.append("--- The Dungeon Master watches, waiting for the next move. ---")
        return "\n".join(parts)

    def adjudicate_rule(self, campaign_id: str, action: str,
                        ruleset: str = "") -> Optional[Dict[str, Any]]:
        """Adjudicate a player action using d20-style dice mechanics."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None
        roll = random.randint(1, 20)
        action_lower = action.lower()
        # Determine DC and modifier based on action type
        if any(w in action_lower for w in ["attack", "strike", "hit", "slash"]):
            dc = 12
            modifier = 5
        elif any(w in action_lower for w in ["persuade", "deceive", "intimidate", "charm"]):
            dc = 15
            modifier = 3
        elif any(w in action_lower for w in ["investigate", "perceive", "search", "inspect"]):
            dc = 13
            modifier = 4
        elif any(w in action_lower for w in ["cast", "spell", "magic", "invoke"]):
            dc = 14
            modifier = 5
        elif any(w in action_lower for w in ["sneak", "hide", "stealth", "pick"]):
            dc = 13
            modifier = 4
        elif any(w in action_lower for w in ["climb", "jump", "swim", "acrobatics"]):
            dc = 12
            modifier = 3
        else:
            dc = 12
            modifier = 2
        total = roll + modifier
        success = total >= dc
        margin = total - dc
        if margin >= 10:
            outcome = "critical_success"
        elif success:
            outcome = "success"
        elif margin <= -10:
            outcome = "critical_failure"
        else:
            outcome = "failure"
        narrative = (f"The d20 lands on {roll}. With a +{modifier} modifier, "
                     f"the total is {total} against DC {dc}. "
                     f"The action {'succeeds brilliantly' if outcome == 'critical_success' else 'succeeds' if success else 'fails disastrously' if outcome == 'critical_failure' else 'fails'}.")
        self._emit(DungeonMasterEventKind.PLAYER_ACTION.value,
                   campaign_id=campaign_id, action=action,
                   roll=roll, total=total, dc=dc, success=success)
        return {
            "campaign_id": campaign_id,
            "action": action,
            "ruleset": ruleset or "default",
            "d20_roll": roll,
            "modifier": modifier,
            "total": total,
            "difficulty_class": dc,
            "success": success,
            "margin": margin,
            "outcome": outcome,
            "narrative": narrative,
        }

    def calculate_encounter_difficulty(self, party_level: int,
                                       party_size: int,
                                       enemy_cr: float) -> Optional[str]:
        """Calculate encounter difficulty from party capability and enemy threat."""
        if party_level <= 0 or party_size <= 0:
            return EncounterDifficulty.TRIVIAL.value
        party_strength = party_level * party_size
        if enemy_cr <= 0:
            return EncounterDifficulty.TRIVIAL.value
        ratio = enemy_cr / party_strength
        if ratio < 0.25:
            return EncounterDifficulty.TRIVIAL.value
        elif ratio < 0.5:
            return EncounterDifficulty.EASY.value
        elif ratio < 0.75:
            return EncounterDifficulty.MEDIUM.value
        elif ratio < 1.0:
            return EncounterDifficulty.HARD.value
        elif ratio < 1.5:
            return EncounterDifficulty.DEADLY.value
        else:
            return EncounterDifficulty.BOSS.value

    # ------------------------------------------------------------------
    # Lifecycle and Observability
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        with _lock:
            self._tick_count += 1
            results: Dict[str, Any] = {
                "tick_count": self._tick_count,
                "dt": dt,
                "campaigns_processed": 0,
                "world_states_updated": 0,
                "arcs_advanced": 0,
                "encounters_completed": 0,
                "events_emitted": 0,
            }
            events_before = len(self._events)

            # Advance time in each campaign's world state
            weather_options = ["clear", "cloudy", "rain", "storm", "fog", "snow"]
            for campaign_id, ws in self._world_states.items():
                campaign = self._campaigns.get(campaign_id)
                if not campaign or campaign.status != CampaignStatus.ACTIVE.value:
                    continue
                results["campaigns_processed"] += 1
                ws.time_elapsed += dt
                # Roll over to new day if time exceeds 24 hours
                while ws.time_elapsed >= 24.0:
                    ws.time_elapsed -= 24.0
                    ws.day_count += 1
                    # Randomly shift weather on new days
                    if ws.season != "unknown":
                        ws.weather = random.choice(weather_options)
                results["world_states_updated"] += 1

            # Update stats
            self._stats.active_campaigns = sum(
                1 for c in self._campaigns.values()
                if c.status == CampaignStatus.ACTIVE.value
            )
            self._stats.total_events = len(self._events)
            results["events_emitted"] = len(self._events) - events_before
            self._emit("tick", tick_count=self._tick_count)
            return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_campaigns": len(self._campaigns),
            "active_campaigns": sum(
                1 for c in self._campaigns.values()
                if c.status == CampaignStatus.ACTIVE.value),
            "total_story_arcs": len(self._story_arcs),
            "total_npcs": len(self._npcs),
            "total_moral_choices": len(self._moral_choices),
            "resolved_moral_choices": sum(
                1 for m in self._moral_choices.values() if m.is_resolved),
            "total_consequences": len(self._consequences),
            "applied_consequences": len(self._applied_consequences),
            "total_encounters": len(self._encounters),
            "completed_encounters": sum(
                1 for e in self._encounters.values() if e.is_completed),
            "total_party_members": len(self._parties),
            "total_world_states": len(self._world_states),
            "tick_count": self._tick_count,
            "total_events": len(self._events),
        }

    def reset(self) -> Tuple[bool, str]:
        with _lock:
            self._campaigns.clear()
            self._story_arcs.clear()
            self._npcs.clear()
            self._moral_choices.clear()
            self._consequences.clear()
            self._encounters.clear()
            self._parties.clear()
            self._world_states.clear()
            self._events.clear()
            self._applied_consequences.clear()
            self._stats = DungeonMasterStats()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._emit("reset")
            return True, "reset"

    def get_snapshot(self) -> DungeonMasterSnapshot:
        return DungeonMasterSnapshot(
            timestamp=_now(),
            campaigns_count=len(self._campaigns),
            active_campaigns=sum(
                1 for c in self._campaigns.values()
                if c.status == CampaignStatus.ACTIVE.value),
            npcs_count=len(self._npcs),
            encounters_count=len(self._encounters),
            parties_count=len(self._parties),
            config=self._config,
        )

    def get_stats(self) -> DungeonMasterStats:
        return self._stats

    def set_config(self, updates: Dict[str, Any]) -> Tuple[bool, str, DungeonMasterConfig]:
        with _lock:
            if "max_campaigns" in updates:
                self._config.max_campaigns = max(1, _safe_int(updates["max_campaigns"], 10))
            if "max_npcs_per_campaign" in updates:
                self._config.max_npcs_per_campaign = max(
                    1, _safe_int(updates["max_npcs_per_campaign"], 50))
            if "max_party_size" in updates:
                self._config.max_party_size = max(
                    1, _safe_int(updates["max_party_size"], 6))
            if "story_complexity" in updates:
                self._config.story_complexity = str(updates["story_complexity"])
            if "moral_system_enabled" in updates:
                self._config.moral_system_enabled = bool(updates["moral_system_enabled"])
            if "permadeath" in updates:
                self._config.permadeath = bool(updates["permadeath"])
            if "auto_balance_encounters" in updates:
                self._config.auto_balance_encounters = bool(
                    updates["auto_balance_encounters"])
            if "session_timeout" in updates:
                self._config.session_timeout = max(
                    1, _safe_int(updates["session_timeout"], 240))
            self._emit("config_updated")
            return True, "updated", self._config

    def get_config(self) -> DungeonMasterConfig:
        return self._config

    def list_events(self, limit: int = 100, campaign_id: str = "",
                    event_type: str = "") -> List[DungeonMasterEvent]:
        results = list(reversed(self._events))
        if campaign_id:
            results = [e for e in results if e.campaign_id == campaign_id]
        if event_type:
            results = [e for e in results if e.kind == event_type]
        return results[:limit]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_dungeon_master() -> AIDungeonMaster:
    """Return the singleton AIDungeonMaster instance."""
    return AIDungeonMaster.get_instance()