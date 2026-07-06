"""
SparkLabs Agent - Nemesis Director

An AI antagonist director for the SparkLabs AI-native game engine. It spawns
recurring adaptive rivals that learn player weaknesses, evolve through a rank
hierarchy, form political relationships with each other, and resurface after
defeat with new traits. The director fuses emergent narrative, threat
modeling, and player-profile learning into a single intelligent surface that
choreographs signature antagonist arcs without manual scripting.

Architecture:
  NemesisDirector (singleton)
    |-- NemesisProfile, NemesisRelationship, NemesisWeakness,
       NemesisEncounter, NemesisStats, NemesisSnapshot, NemesisEvent
    |-- NemesisRank, NemesisStatus, NemesisTrait, NemesisRelationKind,
       NemesisEventKind

Core Capabilities:
  - spawn_nemesis / get_nemesis / list_nemesis / update_nemesis /
    remove_nemesis: antagonist lifecycle with rank, traits, strengths.
  - promote_nemesis / defeat_nemesis / resurrect_nemesis / exile_nemesis:
    rank transitions and fate orchestration.
  - register_relationship / get_relationship / list_relationships /
    remove_relationship: political graph between antagonists.
  - register_weakness / get_weakness / list_weaknesses: exploitable
    weaknesses discovered by the player.
  - log_encounter / list_encounters: combat history that feeds learning.
  - learn_weakness: infer a new weakness from encounter telemetry.
  - suggest_nemesis_for_player: pick a fitting rival for a player profile.
  - assess_threat: score the threat a nemesis poses to a player.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`NemesisDirector.get_instance` or the module-level
:func:`get_nemesis_director` factory.
"""

from __future__ import annotations

import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_NEMESES: int = 2000
_MAX_RELATIONSHIPS: int = 4000
_MAX_WEAKNESSES: int = 6000
_MAX_ENCOUNTERS: int = 10000
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
    if isinstance(value, (list, tuple, set)):
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
    if value < low:
        return low
    if value > high:
        return high
    return value


# Trait affinity weights for threat assessment
_TRAIT_THREAT_WEIGHTS: Dict[str, float] = {
    "ruthless": 1.3,
    "cunning": 1.25,
    "brave": 1.1,
    "cowardly": 0.7,
    "arrogant": 0.9,
    "humble": 1.05,
    "ambitious": 1.2,
    "loyal": 1.0,
    "treacherous": 1.15,
    "ancient": 1.4,
}

_RANK_THREAT_BASE: Dict[str, float] = {
    "grunt": 0.2,
    "captain": 0.45,
    "warchief": 0.7,
    "overlord": 0.95,
}

_RANK_ORDER: List[str] = ["grunt", "captain", "warchief", "overlord"]


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class NemesisRank(Enum):
    """Rank tiers in the antagonist hierarchy."""
    GRUNT = "grunt"
    CAPTAIN = "captain"
    WARCHIEF = "warchief"
    OVERLORD = "overlord"


class NemesisStatus(Enum):
    """Lifecycle status of a nemesis."""
    ALIVE = "alive"
    DEFEATED = "defeated"
    RESURRECTED = "resurrected"
    EXILED = "exiled"
    PROMOTED = "promoted"


class NemesisTrait(Enum):
    """Personality traits that influence threat and behavior."""
    RUTHLESS = "ruthless"
    CUNNING = "cunning"
    BRAVE = "brave"
    COWARDLY = "cowardly"
    ARROGANT = "arrogant"
    HUMBLE = "humble"
    AMBITIOUS = "ambitious"
    LOYAL = "loyal"
    TREACHEROUS = "treacherous"
    ANCIENT = "ancient"


class NemesisRelationKind(Enum):
    """Relationship types between two nemeses."""
    RIVAL = "rival"
    ALLY = "ally"
    SUBORDINATE = "subordinate"
    SUPERIOR = "superior"
    NEMESIS = "nemesis"


class NemesisEventKind(Enum):
    """Audit event types emitted by the nemesis director."""
    NEMESIS_SPAWNED = "nemesis_spawned"
    NEMESIS_DEFEATED = "nemesis_defeated"
    NEMESIS_PROMOTED = "nemesis_promoted"
    NEMESIS_RESURRECTED = "nemesis_resurrected"
    NEMESIS_EXILED = "nemesis_exiled"
    NEMESIS_REMOVED = "nemesis_removed"
    RELATIONSHIP_FORMED = "relationship_formed"
    RELATIONSHIP_REMOVED = "relationship_removed"
    WEAKNESS_REGISTERED = "weakness_registered"
    WEAKNESS_LEARNED = "weakness_learned"
    ENCOUNTER_LOGGED = "encounter_logged"
    THREAT_ASSESSED = "threat_assessed"
    SUGGESTION_ISSUED = "suggestion_issued"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class NemesisWeakness:
    """An exploitable weakness discovered by the player."""
    weakness_id: str
    kind: str = "vulnerable_element"
    description: str = ""
    discovered: bool = False
    exploit_count: int = 0
    effectiveness: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NemesisProfile:
    """A recurring adaptive antagonist."""
    nemesis_id: str
    name: str = ""
    title: str = ""
    description: str = ""
    rank: str = NemesisRank.GRUNT.value
    status: str = NemesisStatus.ALIVE.value
    traits: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    body_type: str = "humanoid"
    weapon: str = "sword"
    faction: str = ""
    lore: str = ""
    encounter_count: int = 0
    defeat_count: int = 0
    kill_count_player: int = 0
    last_encounter_ms: int = 0
    power_level: float = 0.3
    fear_score: float = 0.0
    hatred_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NemesisRelationship:
    """A political relationship between two nemeses."""
    relation_id: str
    nemesis_a_id: str = ""
    nemesis_b_id: str = ""
    kind: str = NemesisRelationKind.RIVAL.value
    strength: float = 0.5
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NemesisEncounter:
    """A combat encounter between a nemesis and a player."""
    encounter_id: str
    nemesis_id: str = ""
    player_id: str = ""
    outcome: str = "player_victory"
    duration_ms: int = 0
    player_damage_dealt: float = 0.0
    player_damage_taken: float = 0.0
    weakness_exploited: str = ""
    location: str = ""
    timestamp_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NemesisStats:
    """Cumulative statistics for the nemesis director."""
    total_nemeses: int = 0
    total_relationships: int = 0
    total_weaknesses: int = 0
    total_encounters: int = 0
    total_defeats: int = 0
    total_resurrections: int = 0
    total_promotions: int = 0
    total_exiles: int = 0
    total_suggestions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NemesisSnapshot:
    """Point-in-time snapshot of the entire nemesis director state."""
    nemeses: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, Any] = field(default_factory=dict)
    weaknesses: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NemesisEvent:
    """An audit event emitted by the nemesis director."""
    event_id: str
    kind: str = NemesisEventKind.NEMESIS_SPAWNED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Director Singleton
# ---------------------------------------------------------------------------


class NemesisDirector:
    """Singleton AI director that choreographs adaptive antagonists."""

    _instance: Optional["NemesisDirector"] = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._nemeses: Dict[str, NemesisProfile] = {}
        self._relationships: Dict[str, NemesisRelationship] = {}
        self._weaknesses: Dict[str, NemesisWeakness] = {}
        self._weaknesses_by_nemesis: Dict[str, List[str]] = {}
        self._encounters: List[NemesisEncounter] = []
        self._audit: List[NemesisEvent] = []
        self._defeats: int = 0
        self._resurrections: int = 0
        self._promotions: int = 0
        self._exiles: int = 0
        self._suggestions: int = 0
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "NemesisDirector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = cls()
                    inst._initialize()
                    cls._instance = inst
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        """Seed a small set of default nemeses, weaknesses, and a relationship."""
        grish = NemesisProfile(
            nemesis_id="nms_grish_ironmaw",
            name="Grish Ironmaw",
            title="The Unbroken",
            description="A warchief known for relentless frontal assaults.",
            rank=NemesisRank.WARCHIEF.value,
            status=NemesisStatus.ALIVE.value,
            traits=[NemesisTrait.RUTHLESS.value, NemesisTrait.BRAVE.value, NemesisTrait.ANCIENT.value],
            strengths=["heavy_armor", "shield_wall", "fear_aura"],
            weaknesses=[],
            body_type="orc",
            weapon="war_hammer",
            faction="iron_legion",
            lore="Forged in the volcanic forges of Mount Karth, Grish has never retreated.",
            encounter_count=2,
            defeat_count=0,
            kill_count_player=0,
            power_level=0.72,
            fear_score=0.6,
            hatred_score=0.4,
        )
        self._nemeses[grish.nemesis_id] = grish
        self._record_event(NemesisEventKind.NEMESIS_SPAWNED, {
            "nemesis_id": grish.nemesis_id, "name": grish.name, "rank": grish.rank,
        })

        vael = NemesisProfile(
            nemesis_id="nms_vael_whispers",
            name="Vael Whispers",
            title="The Shadowblade",
            description="A cunning assassin who strikes from stealth.",
            rank=NemesisRank.CAPTAIN.value,
            status=NemesisStatus.ALIVE.value,
            traits=[NemesisTrait.CUNNING.value, NemesisTrait.TREACHEROUS.value, NemesisTrait.AMBITIOUS.value],
            strengths=["stealth", "poison", "dual_wield"],
            weaknesses=[],
            body_type="elf",
            weapon="twin_daggers",
            faction="shadow_court",
            lore="Vael once served the royal family before turning to the shadow court.",
            encounter_count=1,
            defeat_count=0,
            kill_count_player=0,
            power_level=0.55,
            fear_score=0.3,
            hatred_score=0.5,
        )
        self._nemeses[vael.nemesis_id] = vael
        self._record_event(NemesisEventKind.NEMESIS_SPAWNED, {
            "nemesis_id": vael.nemesis_id, "name": vael.name, "rank": vael.rank,
        })

        weakness = NemesisWeakness(
            weakness_id="wkn_grish_frost",
            kind="vulnerable_element",
            description="Grish takes double damage from frost attacks.",
            discovered=True,
            exploit_count=1,
            effectiveness=0.8,
        )
        self._weaknesses[weakness.weakness_id] = weakness
        self._weaknesses_by_nemesis.setdefault(grish.nemesis_id, []).append(weakness.weakness_id)
        grish.weaknesses.append(weakness.weakness_id)
        self._record_event(NemesisEventKind.WEAKNESS_REGISTERED, {
            "weakness_id": weakness.weakness_id, "nemesis_id": grish.nemesis_id,
        })

        relation = NemesisRelationship(
            relation_id="rel_grish_vael",
            nemesis_a_id=grish.nemesis_id,
            nemesis_b_id=vael.nemesis_id,
            kind=NemesisRelationKind.RIVAL.value,
            strength=0.7,
            history=[{"event": "border_skirmish", "outcome": "stalemate"}],
        )
        self._relationships[relation.relation_id] = relation
        self._record_event(NemesisEventKind.RELATIONSHIP_FORMED, {
            "relation_id": relation.relation_id,
            "nemesis_a_id": relation.nemesis_a_id,
            "nemesis_b_id": relation.nemesis_b_id,
        })

        encounter = NemesisEncounter(
            encounter_id="enc_seed_1",
            nemesis_id=grish.nemesis_id,
            player_id="player_1",
            outcome="player_retreat",
            duration_ms=45000,
            player_damage_dealt=320.0,
            player_damage_taken=580.0,
            weakness_exploited="wkn_grish_frost",
            location="mount_karth_pass",
            timestamp_ms=1719900000000,
        )
        self._encounters.append(encounter)
        self._record_event(NemesisEventKind.ENCOUNTER_LOGGED, {
            "encounter_id": encounter.encounter_id,
            "nemesis_id": encounter.nemesis_id,
            "outcome": encounter.outcome,
        })

    # ------------------------------------------------------------------
    # Audit Helpers
    # ------------------------------------------------------------------

    def _record_event(self, kind: NemesisEventKind, payload: Dict[str, Any]) -> None:
        event = NemesisEvent(
            event_id=_new_id("evt"),
            kind=kind.value,
            payload=dict(payload),
            timestamp=_now(),
        )
        self._audit.append(event)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Nemesis Lifecycle
    # ------------------------------------------------------------------

    def spawn_nemesis(
        self,
        nemesis_id: str = "",
        name: str = "",
        title: str = "",
        description: str = "",
        rank: str = NemesisRank.GRUNT.value,
        status: str = NemesisStatus.ALIVE.value,
        traits: Optional[List[str]] = None,
        strengths: Optional[List[str]] = None,
        weaknesses: Optional[List[str]] = None,
        body_type: str = "humanoid",
        weapon: str = "sword",
        faction: str = "",
        lore: str = "",
        power_level: float = 0.3,
        fear_score: float = 0.0,
        hatred_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NemesisProfile:
        with self._lock:
            nid = nemesis_id or _new_id("nms")
            profile = NemesisProfile(
                nemesis_id=nid,
                name=name,
                title=title,
                description=description,
                rank=rank,
                status=status,
                traits=list(traits or []),
                strengths=list(strengths or []),
                weaknesses=list(weaknesses or []),
                body_type=body_type,
                weapon=weapon,
                faction=faction,
                lore=lore,
                power_level=_clamp(_safe_float(power_level, 0.3)),
                fear_score=_clamp(_safe_float(fear_score, 0.0)),
                hatred_score=_clamp(_safe_float(hatred_score, 0.0)),
                metadata=dict(metadata or {}),
            )
            self._nemeses[nid] = profile
            _evict_fifo_dict(self._nemeses, _MAX_NEMESES)
            self._record_event(NemesisEventKind.NEMESIS_SPAWNED, {
                "nemesis_id": nid, "name": name, "rank": rank,
            })
            return profile

    def get_nemesis(self, nemesis_id: str) -> Optional[NemesisProfile]:
        with self._lock:
            return self._nemeses.get(nemesis_id)

    def list_nemeses(
        self,
        rank: str = "",
        status: str = "",
        faction: str = "",
        limit: int = 100,
    ) -> List[NemesisProfile]:
        with self._lock:
            results: List[NemesisProfile] = []
            for profile in self._nemeses.values():
                if rank and profile.rank != rank:
                    continue
                if status and profile.status != status:
                    continue
                if faction and profile.faction != faction:
                    continue
                results.append(profile)
            return results[:max(0, int(limit))]

    def update_nemesis(self, nemesis_id: str, **kwargs: Any) -> Optional[NemesisProfile]:
        with self._lock:
            profile = self._nemeses.get(nemesis_id)
            if profile is None:
                return None
            for key, value in kwargs.items():
                if not hasattr(profile, key):
                    continue
                if key in ("power_level", "fear_score", "hatred_score"):
                    setattr(profile, key, _clamp(_safe_float(value, getattr(profile, key))))
                elif key in ("encounter_count", "defeat_count", "kill_count_player", "last_encounter_ms"):
                    setattr(profile, key, _safe_int(value, getattr(profile, key)))
                elif key in ("traits", "strengths", "weaknesses"):
                    setattr(profile, key, list(value) if isinstance(value, (list, tuple)) else getattr(profile, key))
                else:
                    setattr(profile, key, value)
            return profile

    def remove_nemesis(self, nemesis_id: str) -> bool:
        with self._lock:
            profile = self._nemeses.pop(nemesis_id, None)
            if profile is None:
                return False
            for rel in list(self._relationships.values()):
                if rel.nemesis_a_id == nemesis_id or rel.nemesis_b_id == nemesis_id:
                    self._relationships.pop(rel.relation_id, None)
            for wid in list(self._weaknesses_by_nemesis.get(nemesis_id, [])):
                self._weaknesses.pop(wid, None)
            self._weaknesses_by_nemesis.pop(nemesis_id, None)
            self._record_event(NemesisEventKind.NEMESIS_REMOVED, {"nemesis_id": nemesis_id})
            return True

    def promote_nemesis(self, nemesis_id: str) -> Optional[NemesisProfile]:
        with self._lock:
            profile = self._nemeses.get(nemesis_id)
            if profile is None:
                return None
            current_idx = _RANK_ORDER.index(profile.rank) if profile.rank in _RANK_ORDER else 0
            if current_idx < len(_RANK_ORDER) - 1:
                profile.rank = _RANK_ORDER[current_idx + 1]
                profile.status = NemesisStatus.PROMOTED.value
                profile.power_level = _clamp(profile.power_level + 0.15)
                self._promotions += 1
                self._record_event(NemesisEventKind.NEMESIS_PROMOTED, {
                    "nemesis_id": nemesis_id, "new_rank": profile.rank,
                })
            return profile

    def defeat_nemesis(self, nemesis_id: str) -> Optional[NemesisProfile]:
        with self._lock:
            profile = self._nemeses.get(nemesis_id)
            if profile is None:
                return None
            profile.status = NemesisStatus.DEFEATED.value
            profile.defeat_count += 1
            self._defeats += 1
            self._record_event(NemesisEventKind.NEMESIS_DEFEATED, {
                "nemesis_id": nemesis_id, "defeat_count": profile.defeat_count,
            })
            return profile

    def resurrect_nemesis(self, nemesis_id: str) -> Optional[NemesisProfile]:
        with self._lock:
            profile = self._nemeses.get(nemesis_id)
            if profile is None:
                return None
            profile.status = NemesisStatus.RESURRECTED.value
            profile.power_level = _clamp(profile.power_level + 0.1)
            profile.hatred_score = _clamp(profile.hatred_score + 0.2)
            self._resurrections += 1
            self._record_event(NemesisEventKind.NEMESIS_RESURRECTED, {
                "nemesis_id": nemesis_id,
                "new_power_level": profile.power_level,
            })
            return profile

    def exile_nemesis(self, nemesis_id: str) -> Optional[NemesisProfile]:
        with self._lock:
            profile = self._nemeses.get(nemesis_id)
            if profile is None:
                return None
            profile.status = NemesisStatus.EXILED.value
            self._exiles += 1
            self._record_event(NemesisEventKind.NEMESIS_EXILED, {
                "nemesis_id": nemesis_id,
            })
            return profile

    # ------------------------------------------------------------------
    # Relationship Management
    # ------------------------------------------------------------------

    def register_relationship(
        self,
        relation_id: str = "",
        nemesis_a_id: str = "",
        nemesis_b_id: str = "",
        kind: str = NemesisRelationKind.RIVAL.value,
        strength: float = 0.5,
        history: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NemesisRelationship:
        with self._lock:
            rid = relation_id or _new_id("rel")
            relation = NemesisRelationship(
                relation_id=rid,
                nemesis_a_id=nemesis_a_id,
                nemesis_b_id=nemesis_b_id,
                kind=kind,
                strength=_clamp(_safe_float(strength, 0.5)),
                history=list(history or []),
                metadata=dict(metadata or {}),
            )
            self._relationships[rid] = relation
            _evict_fifo_dict(self._relationships, _MAX_RELATIONSHIPS)
            self._record_event(NemesisEventKind.RELATIONSHIP_FORMED, {
                "relation_id": rid, "kind": kind,
                "nemesis_a_id": nemesis_a_id, "nemesis_b_id": nemesis_b_id,
            })
            return relation

    def get_relationship(self, relation_id: str) -> Optional[NemesisRelationship]:
        with self._lock:
            return self._relationships.get(relation_id)

    def list_relationships(
        self,
        nemesis_id: str = "",
        kind: str = "",
        limit: int = 100,
    ) -> List[NemesisRelationship]:
        with self._lock:
            results: List[NemesisRelationship] = []
            for rel in self._relationships.values():
                if nemesis_id and rel.nemesis_a_id != nemesis_id and rel.nemesis_b_id != nemesis_id:
                    continue
                if kind and rel.kind != kind:
                    continue
                results.append(rel)
            return results[:max(0, int(limit))]

    def remove_relationship(self, relation_id: str) -> bool:
        with self._lock:
            rel = self._relationships.pop(relation_id, None)
            if rel is None:
                return False
            self._record_event(NemesisEventKind.RELATIONSHIP_REMOVED, {
                "relation_id": relation_id,
            })
            return True

    # ------------------------------------------------------------------
    # Weakness Management
    # ------------------------------------------------------------------

    def register_weakness(
        self,
        nemesis_id: str,
        weakness_id: str = "",
        kind: str = "vulnerable_element",
        description: str = "",
        discovered: bool = False,
        exploit_count: int = 0,
        effectiveness: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[NemesisWeakness]:
        with self._lock:
            profile = self._nemeses.get(nemesis_id)
            if profile is None:
                return None
            wid = weakness_id or _new_id("wkn")
            weakness = NemesisWeakness(
                weakness_id=wid,
                kind=kind,
                description=description,
                discovered=bool(discovered),
                exploit_count=_safe_int(exploit_count, 0),
                effectiveness=_clamp(_safe_float(effectiveness, 0.5)),
                metadata=dict(metadata or {}),
            )
            self._weaknesses[wid] = weakness
            self._weaknesses_by_nemesis.setdefault(nemesis_id, []).append(wid)
            if wid not in profile.weaknesses:
                profile.weaknesses.append(wid)
            _evict_fifo_dict(self._weaknesses, _MAX_WEAKNESSES)
            self._record_event(NemesisEventKind.WEAKNESS_REGISTERED, {
                "weakness_id": wid, "nemesis_id": nemesis_id,
            })
            return weakness

    def get_weakness(self, weakness_id: str) -> Optional[NemesisWeakness]:
        with self._lock:
            return self._weaknesses.get(weakness_id)

    def list_weaknesses(
        self,
        nemesis_id: str = "",
        discovered: Optional[bool] = None,
        limit: int = 100,
    ) -> List[NemesisWeakness]:
        with self._lock:
            results: List[NemesisWeakness] = []
            if nemesis_id:
                wids = self._weaknesses_by_nemesis.get(nemesis_id, [])
                for wid in wids:
                    w = self._weaknesses.get(wid)
                    if w is None:
                        continue
                    if discovered is not None and w.discovered != discovered:
                        continue
                    results.append(w)
            else:
                for w in self._weaknesses.values():
                    if discovered is not None and w.discovered != discovered:
                        continue
                    results.append(w)
            return results[:max(0, int(limit))]

    # ------------------------------------------------------------------
    # Encounter Logging and Learning
    # ------------------------------------------------------------------

    def log_encounter(
        self,
        nemesis_id: str = "",
        player_id: str = "",
        outcome: str = "player_victory",
        duration_ms: int = 0,
        player_damage_dealt: float = 0.0,
        player_damage_taken: float = 0.0,
        weakness_exploited: str = "",
        location: str = "",
        timestamp_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NemesisEncounter:
        with self._lock:
            eid = _new_id("enc")
            encounter = NemesisEncounter(
                encounter_id=eid,
                nemesis_id=nemesis_id,
                player_id=player_id,
                outcome=outcome,
                duration_ms=_safe_int(duration_ms, 0),
                player_damage_dealt=_safe_float(player_damage_dealt, 0.0),
                player_damage_taken=_safe_float(player_damage_taken, 0.0),
                weakness_exploited=weakness_exploited,
                location=location,
                timestamp_ms=_safe_int(timestamp_ms, 0),
                metadata=dict(metadata or {}),
            )
            self._encounters.append(encounter)
            _evict_fifo_list(self._encounters, _MAX_ENCOUNTERS)
            profile = self._nemeses.get(nemesis_id)
            if profile is not None:
                profile.encounter_count += 1
                profile.last_encounter_ms = _safe_int(timestamp_ms, 0)
                if outcome == "player_victory":
                    pass
                elif outcome == "nemesis_victory":
                    profile.kill_count_player += 1
            if weakness_exploited:
                weakness = self._weaknesses.get(weakness_exploited)
                if weakness is not None:
                    weakness.exploit_count += 1
                    weakness.discovered = True
            self._record_event(NemesisEventKind.ENCOUNTER_LOGGED, {
                "encounter_id": eid, "nemesis_id": nemesis_id, "outcome": outcome,
            })
            return encounter

    def list_encounters(
        self,
        nemesis_id: str = "",
        player_id: str = "",
        outcome: str = "",
        limit: int = 100,
    ) -> List[NemesisEncounter]:
        with self._lock:
            results: List[NemesisEncounter] = []
            for enc in reversed(self._encounters):
                if nemesis_id and enc.nemesis_id != nemesis_id:
                    continue
                if player_id and enc.player_id != player_id:
                    continue
                if outcome and enc.outcome != outcome:
                    continue
                results.append(enc)
            return results[:max(0, int(limit))]

    def learn_weakness(
        self,
        nemesis_id: str,
        player_id: str,
        recent_encounters: int = 5,
    ) -> Optional[NemesisWeakness]:
        """Infer a new weakness from encounter telemetry."""
        with self._lock:
            encounters = self.list_encounters(nemesis_id=nemesis_id, player_id=player_id, limit=recent_encounters)
            if len(encounters) < 2:
                return None
            total_damage_dealt = sum(e.player_damage_dealt for e in encounters)
            avg_damage = total_damage_dealt / max(1, len(encounters))
            existing_wids = set(self._weaknesses_by_nemesis.get(nemesis_id, []))
            inferred_kind = "vulnerable_element"
            if avg_damage > 400:
                inferred_kind = "structural_weak_point"
            elif avg_damage < 150:
                inferred_kind = "resist_gap"
            new_weakness = self.register_weakness(
                nemesis_id=nemesis_id,
                kind=inferred_kind,
                description=f"Inferred weakness from {len(encounters)} encounters with avg damage {avg_damage:.1f}.",
                discovered=True,
                exploit_count=len(encounters),
                effectiveness=_clamp(avg_damage / 600.0),
                metadata={"player_id": player_id, "inferred": True},
            )
            if new_weakness is not None:
                self._record_event(NemesisEventKind.WEAKNESS_LEARNED, {
                    "weakness_id": new_weakness.weakness_id,
                    "nemesis_id": nemesis_id,
                    "kind": inferred_kind,
                })
            return new_weakness

    # ------------------------------------------------------------------
    # Intelligence
    # ------------------------------------------------------------------

    def suggest_nemesis_for_player(
        self,
        player_id: str,
        player_skill: float = 0.5,
        preferred_faction: str = "",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Pick fitting rivals for a player profile."""
        with self._lock:
            suggestions: List[Dict[str, Any]] = []
            for profile in self._nemeses.values():
                if profile.status not in (NemesisStatus.ALIVE.value, NemesisStatus.RESURRECTED.value):
                    continue
                if preferred_faction and profile.faction != preferred_faction:
                    continue
                threat = self._compute_threat(profile, player_skill)
                fit = _clamp(1.0 - abs(threat - player_skill))
                if profile.kill_count_player > 0:
                    fit = _clamp(fit + 0.15)
                suggestions.append({
                    "nemesis_id": profile.nemesis_id,
                    "name": profile.name,
                    "rank": profile.rank,
                    "threat": round(threat, 3),
                    "fit_score": round(fit, 3),
                    "reason": "matching_threat" if fit > 0.6 else "stretch_target",
                })
            suggestions.sort(key=lambda s: s.get("fit_score", 0.0), reverse=True)
            self._suggestions += 1
            self._record_event(NemesisEventKind.SUGGESTION_ISSUED, {
                "player_id": player_id, "count": len(suggestions),
            })
            return suggestions[:max(0, int(limit))]

    def assess_threat(self, nemesis_id: str, player_skill: float = 0.5) -> Optional[Dict[str, Any]]:
        """Score the threat a nemesis poses to a player."""
        with self._lock:
            profile = self._nemeses.get(nemesis_id)
            if profile is None:
                return None
            threat = self._compute_threat(profile, player_skill)
            delta = threat - player_skill
            if delta > 0.2:
                verdict = "overwhelming"
            elif delta > 0.0:
                verdict = "challenging"
            elif delta > -0.2:
                verdict = "balanced"
            else:
                verdict = "trivial"
            self._record_event(NemesisEventKind.THREAT_ASSESSED, {
                "nemesis_id": nemesis_id, "threat": threat, "verdict": verdict,
            })
            return {
                "nemesis_id": nemesis_id,
                "name": profile.name,
                "rank": profile.rank,
                "threat_score": round(threat, 3),
                "player_skill": _clamp(_safe_float(player_skill, 0.5)),
                "delta": round(delta, 3),
                "verdict": verdict,
                "power_level": profile.power_level,
                "fear_score": profile.fear_score,
                "hatred_score": profile.hatred_score,
            }

    def _compute_threat(self, profile: NemesisProfile, player_skill: float = 0.5) -> float:
        base = _RANK_THREAT_BASE.get(profile.rank, 0.3)
        trait_bonus = 1.0
        for trait in profile.traits:
            trait_bonus *= _TRAIT_THREAT_WEIGHTS.get(trait, 1.0)
        trait_bonus = _clamp(trait_bonus, 0.5, 2.0)
        threat = base * 0.6 + profile.power_level * 0.3 + (trait_bonus - 1.0) * 0.1
        if profile.kill_count_player > 0:
            threat = _clamp(threat + 0.05 * profile.kill_count_player)
        return _clamp(threat)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[NemesisEvent]:
        with self._lock:
            return list(self._audit)[:max(0, int(limit))]

    def get_stats(self) -> NemesisStats:
        with self._lock:
            return NemesisStats(
                total_nemeses=len(self._nemeses),
                total_relationships=len(self._relationships),
                total_weaknesses=len(self._weaknesses),
                total_encounters=len(self._encounters),
                total_defeats=self._defeats,
                total_resurrections=self._resurrections,
                total_promotions=self._promotions,
                total_exiles=self._exiles,
                total_suggestions=self._suggestions,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "nemeses": len(self._nemeses),
                "relationships": len(self._relationships),
                "weaknesses": len(self._weaknesses),
                "encounters": len(self._encounters),
                "defeats": self._defeats,
                "resurrections": self._resurrections,
                "promotions": self._promotions,
                "exiles": self._exiles,
                "suggestions": self._suggestions,
                "events": len(self._audit),
            }

    def get_snapshot(self) -> NemesisSnapshot:
        with self._lock:
            return NemesisSnapshot(
                nemeses={nid: n.to_dict() for nid, n in self._nemeses.items()},
                relationships={rid: r.to_dict() for rid, r in self._relationships.items()},
                weaknesses={wid: w.to_dict() for wid, w in self._weaknesses.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._nemeses.clear()
            self._relationships.clear()
            self._weaknesses.clear()
            self._weaknesses_by_nemesis.clear()
            self._encounters.clear()
            self._audit.clear()
            self._defeats = 0
            self._resurrections = 0
            self._promotions = 0
            self._exiles = 0
            self._suggestions = 0
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_nemesis_director() -> NemesisDirector:
    return NemesisDirector.get_instance()
