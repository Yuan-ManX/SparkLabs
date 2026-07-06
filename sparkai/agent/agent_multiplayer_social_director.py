"""
SparkLabs Agent - AI Multiplayer Social Director

A runtime fusion module that orchestrates live multiplayer experiences by
fusing skill rating, social graph analysis, and real-time engagement
signals. The director maintains player skill profiles, builds and
traverses the social graph (friendships, guilds, rivalries), runs
skill-aware and social-aware matchmaking, composes balanced teams,
and triggers live social events (tournaments, guild wars, community
challenges) based on population health and engagement trends.

This module embodies the AI-native principle: multiplayer is not a
static lobby system but an intelligent agent that continuously reasons
about population dynamics, social cohesion, and competitive balance
to deliver the right match to the right player at the right time.

Architecture:
  MultiplayerSocialDirector (singleton)
    |-- SkillProfile, SocialEdge, SocialCluster, MatchmakingTicket,
        MatchResult, TeamComposition, SocialEvent, MultiplayerStats,
        MultiplayerSnapshot, MultiplayerEvent
    |-- SkillTier, SocialRelation, MatchmakingStrategy, TeamRole,
        MatchOutcome, SocialEventType, EventStatus,
        MultiplayerEventKind

Core Capabilities:
  - register_player / update_player / get_player / list_players /
    delete_player: skill profile management with rating and tier.
  - add_relation / remove_relation / get_relation / list_relations /
    get_social_graph: social graph management with relation types.
  - detect_clusters / get_cluster / list_clusters: social cluster
    detection grouping players by connectivity and proximity.
  - create_ticket / get_ticket / list_tickets / cancel_ticket:
    matchmaking ticket lifecycle with strategy selection.
  - find_match / get_match / list_matches: skill-aware and
    social-aware matchmaking with team composition.
  - compose_teams / get_team: balanced team composition by role
    and skill distribution.
  - record_result / get_result / list_results: match outcome
    tracking with skill rating updates.
  - create_social_event / update_social_event / launch_social_event /
    complete_social_event / list_social_events: live social event
    lifecycle (tournaments, guild wars, community challenges).
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PLAYERS: int = 10000
_MAX_RELATIONS: int = 50000
_MAX_CLUSTERS: int = 500
_MAX_TICKETS: int = 1000
_MAX_MATCHES: int = 5000
_MAX_RESULTS: int = 10000
_MAX_SOCIAL_EVENTS: int = 200
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


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class SkillTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    UNRANKED = "unranked"


class SocialRelation(Enum):
    FRIEND = "friend"
    GUILD_MEMBER = "guild_member"
    RIVAL = "rival"
    BLOCKED = "blocked"
    MENTOR = "mentor"
    MENTEE = "mentee"
    TEAMMATE = "teammate"


class MatchmakingStrategy(Enum):
    SKILL_ONLY = "skill_only"
    SKILL_AND_SOCIAL = "skill_and_social"
    SOCIAL_FIRST = "social_first"
    RANKED = "ranked"
    CASUAL = "casual"
    TOURNAMENT = "tournament"


class TeamRole(Enum):
    LEADER = "leader"
    DPS = "dps"
    TANK = "tank"
    SUPPORT = "support"
    FLEX = "flex"
    UNASSIGNED = "unassigned"


class MatchOutcome(Enum):
    PENDING = "pending"
    TEAM_A_WIN = "team_a_win"
    TEAM_B_WIN = "team_b_win"
    DRAW = "draw"
    FORFEIT = "forfeit"
    CANCELLED = "cancelled"


class SocialEventType(Enum):
    TOURNAMENT = "tournament"
    GUILD_WAR = "guild_war"
    COMMUNITY_CHALLENGE = "community_challenge"
    SEASONAL_EVENT = "seasonal_event"
    FRIENDLY_SCRIM = "friendly_scrim"
    CUSTOM = "custom"


class EventStatus(Enum):
    DRAFT = "draft"
    ANNOUNCED = "announced"
    REGISTRATION_OPEN = "registration_open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MultiplayerEventKind(Enum):
    PLAYER_REGISTERED = "player_registered"
    PLAYER_UPDATED = "player_updated"
    PLAYER_REMOVED = "player_removed"
    RELATION_ADDED = "relation_added"
    RELATION_REMOVED = "relation_removed"
    CLUSTER_DETECTED = "cluster_detected"
    TICKET_CREATED = "ticket_created"
    TICKET_CANCELLED = "ticket_cancelled"
    MATCH_FOUND = "match_found"
    MATCH_COMPLETED = "match_completed"
    TEAMS_COMPOSED = "teams_composed"
    SOCIAL_EVENT_CREATED = "social_event_created"
    SOCIAL_EVENT_LAUNCHED = "social_event_launched"
    SOCIAL_EVENT_COMPLETED = "social_event_completed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SkillProfile:
    """A player's multiplayer skill profile."""
    player_id: str
    display_name: str = ""
    skill_rating: float = 1000.0
    skill_tier: SkillTier = SkillTier.UNRANKED
    confidence: float = 0.0
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    preferred_roles: List[str] = field(default_factory=list)
    peak_rating: float = 1000.0
    current_streak: int = 0
    last_match_at: str = ""
    is_online: bool = False
    is_in_match: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocialEdge:
    """A relationship edge in the social graph."""
    edge_id: str
    source_player: str
    target_player: str
    relation: SocialRelation = SocialRelation.FRIEND
    strength: float = 1.0
    guild_id: str = ""
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocialCluster:
    """A detected cluster of socially connected players."""
    cluster_id: str
    player_ids: List[str] = field(default_factory=list)
    cluster_type: str = "friend_group"
    cohesion_score: float = 0.0
    avg_skill: float = 0.0
    size: int = 0
    detected_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchmakingTicket:
    """A matchmaking request from a player or party."""
    ticket_id: str
    player_ids: List[str] = field(default_factory=list)
    strategy: MatchmakingStrategy = MatchmakingStrategy.SKILL_AND_SOCIAL
    desired_roles: List[str] = field(default_factory=list)
    avg_rating: float = 0.0
    status: str = "queued"
    created_at: str = field(default_factory=_now)
    matched_at: str = ""
    match_id: str = ""
    wait_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TeamComposition:
    """A composed team for a match."""
    team_id: str = ""
    player_ids: List[str] = field(default_factory=list)
    role_assignments: Dict[str, str] = field(default_factory=dict)
    avg_rating: float = 0.0
    balance_score: float = 0.0
    social_cohesion: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchResult:
    """A completed match with outcome and skill adjustments."""
    match_id: str
    ticket_ids: List[str] = field(default_factory=list)
    team_a: TeamComposition = field(default_factory=TeamComposition)
    team_b: TeamComposition = field(default_factory=TeamComposition)
    outcome: MatchOutcome = MatchOutcome.PENDING
    duration_seconds: int = 0
    skill_adjustments: Dict[str, float] = field(default_factory=dict)
    mvp_player_id: str = ""
    score_team_a: int = 0
    score_team_b: int = 0
    started_at: str = ""
    completed_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocialEvent:
    """A live social event like a tournament or guild war."""
    event_id: str
    name: str
    event_type: SocialEventType = SocialEventType.TOURNAMENT
    description: str = ""
    status: EventStatus = EventStatus.DRAFT
    participant_ids: List[str] = field(default_factory=list)
    max_participants: int = 100
    min_skill_rating: float = 0.0
    max_skill_rating: float = 9999.0
    start_time: str = ""
    end_time: str = ""
    prize_pool: str = ""
    rules: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MultiplayerStats:
    total_players: int = 0
    online_players: int = 0
    in_match_players: int = 0
    total_relations: int = 0
    total_clusters: int = 0
    total_tickets: int = 0
    queued_tickets: int = 0
    total_matches: int = 0
    completed_matches: int = 0
    total_results: int = 0
    total_social_events: int = 0
    active_social_events: int = 0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MultiplayerSnapshot:
    players: List[Dict[str, Any]] = field(default_factory=list)
    clusters: List[Dict[str, Any]] = field(default_factory=list)
    tickets: List[Dict[str, Any]] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)
    social_events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MultiplayerEvent:
    event_id: str
    kind: MultiplayerEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Multiplayer Social Director Singleton
# ---------------------------------------------------------------------------


class MultiplayerSocialDirector:
    """AI-native fusion module orchestrating live multiplayer experiences."""

    _instance: Optional["MultiplayerSocialDirector"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "MultiplayerSocialDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "MultiplayerSocialDirector":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._players: Dict[str, SkillProfile] = {}
            self._edges: Dict[str, SocialEdge] = {}
            self._adjacency: Dict[str, Set[str]] = {}
            self._clusters: Dict[str, SocialCluster] = {}
            self._tickets: Dict[str, MatchmakingTicket] = {}
            self._matches: Dict[str, MatchResult] = {}
            self._social_events: Dict[str, SocialEvent] = {}
            self._events: List[MultiplayerEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: MultiplayerEventKind, data: Dict[str, Any]) -> None:
        event = MultiplayerEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _tier_from_rating(self, rating: float) -> SkillTier:
        if rating < 1200:
            return SkillTier.BRONZE
        elif rating < 1400:
            return SkillTier.SILVER
        elif rating < 1600:
            return SkillTier.GOLD
        elif rating < 1800:
            return SkillTier.PLATINUM
        elif rating < 2000:
            return SkillTier.DIAMOND
        elif rating < 2200:
            return SkillTier.MASTER
        else:
            return SkillTier.GRANDMASTER

    def _recalc_profile(self, player: SkillProfile) -> None:
        if player.total_matches > 0:
            player.win_rate = player.wins / player.total_matches
        player.skill_tier = self._tier_from_rating(player.skill_rating)
        if player.skill_rating > player.peak_rating:
            player.peak_rating = player.skill_rating
        player.updated_at = _now()

    # ------------------------------------------------------------------
    # Player Skill Profile Management
    # ------------------------------------------------------------------

    def register_player(self, player_id: str, display_name: str = "",
                        skill_rating: float = 1000.0,
                        preferred_roles: List[str] = None,
                        is_online: bool = False,
                        metadata: Dict[str, Any] = None) -> SkillProfile:
        with self._lock:
            player = SkillProfile(
                player_id=player_id,
                display_name=display_name,
                skill_rating=skill_rating,
                preferred_roles=preferred_roles or [],
                is_online=is_online,
                metadata=metadata or {},
            )
            self._recalc_profile(player)
            self._players[player.player_id] = player
            _evict_fifo_dict(self._players, _MAX_PLAYERS)
            self._adjacency.setdefault(player_id, set())
            self._emit(MultiplayerEventKind.PLAYER_REGISTERED, {"player_id": player_id})
            return player

    def update_player(self, player_id: str, updates: Dict[str, Any]) -> Optional[SkillProfile]:
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                return None
            for k, v in updates.items():
                if k == "skill_tier" and isinstance(v, str):
                    try:
                        v = SkillTier(v)
                    except ValueError:
                        continue
                if hasattr(player, k) and k not in ("player_id", "created_at"):
                    setattr(player, k, v)
            self._recalc_profile(player)
            self._emit(MultiplayerEventKind.PLAYER_UPDATED, {"player_id": player_id})
            return player

    def get_player(self, player_id: str) -> Optional[SkillProfile]:
        with self._lock:
            return self._players.get(player_id)

    def list_players(self, skill_tier: SkillTier = None, is_online: bool = None,
                     limit: int = 100) -> List[SkillProfile]:
        with self._lock:
            items = list(self._players.values())
            if skill_tier is not None:
                items = [p for p in items if p.skill_tier == skill_tier]
            if is_online is not None:
                items = [p for p in items if p.is_online == is_online]
            return items[-limit:]

    def delete_player(self, player_id: str) -> bool:
        with self._lock:
            if player_id not in self._players:
                return False
            del self._players[player_id]
            edges_to_remove = [eid for eid, e in self._edges.items()
                               if e.source_player == player_id or e.target_player == player_id]
            for eid in edges_to_remove:
                del self._edges[eid]
            self._adjacency.pop(player_id, None)
            for adj in self._adjacency.values():
                adj.discard(player_id)
            self._emit(MultiplayerEventKind.PLAYER_REMOVED, {"player_id": player_id})
            return True

    # ------------------------------------------------------------------
    # Social Graph Management
    # ------------------------------------------------------------------

    def add_relation(self, source_player: str, target_player: str,
                     relation: SocialRelation = SocialRelation.FRIEND,
                     strength: float = 1.0, guild_id: str = "",
                     metadata: Dict[str, Any] = None) -> Optional[SocialEdge]:
        with self._lock:
            if source_player not in self._players or target_player not in self._players:
                return None
            if source_player == target_player:
                return None
            edge = SocialEdge(
                edge_id=_new_id("edge"),
                source_player=source_player,
                target_player=target_player,
                relation=relation,
                strength=strength,
                guild_id=guild_id,
                metadata=metadata or {},
            )
            self._edges[edge.edge_id] = edge
            _evict_fifo_dict(self._edges, _MAX_RELATIONS)
            self._adjacency.setdefault(source_player, set()).add(target_player)
            self._adjacency.setdefault(target_player, set()).add(source_player)
            self._emit(MultiplayerEventKind.RELATION_ADDED, {
                "edge_id": edge.edge_id,
                "source": source_player,
                "target": target_player,
                "relation": relation.value,
            })
            return edge

    def remove_relation(self, edge_id: str) -> bool:
        with self._lock:
            edge = self._edges.get(edge_id)
            if edge is None:
                return False
            source, target = edge.source_player, edge.target_player
            del self._edges[edge_id]
            still_connected = any(
                (e.source_player == source and e.target_player == target) or
                (e.source_player == target and e.target_player == source)
                for e in self._edges.values()
            )
            if not still_connected:
                if source in self._adjacency:
                    self._adjacency[source].discard(target)
                if target in self._adjacency:
                    self._adjacency[target].discard(source)
            self._emit(MultiplayerEventKind.RELATION_REMOVED, {"edge_id": edge_id})
            return True

    def get_relation(self, edge_id: str) -> Optional[SocialEdge]:
        with self._lock:
            return self._edges.get(edge_id)

    def list_relations(self, player_id: str = None,
                       relation: SocialRelation = None,
                       limit: int = 100) -> List[SocialEdge]:
        with self._lock:
            items = list(self._edges.values())
            if player_id is not None:
                items = [e for e in items
                         if e.source_player == player_id or e.target_player == player_id]
            if relation is not None:
                items = [e for e in items if e.relation == relation]
            return items[-limit:]

    def get_social_graph(self, player_id: str = None, depth: int = 1) -> Dict[str, Any]:
        with self._lock:
            if player_id:
                visited: Set[str] = {player_id}
                frontier = {player_id}
                for _ in range(depth):
                    next_frontier: Set[str] = set()
                    for node in frontier:
                        for neighbor in self._adjacency.get(node, set()):
                            if neighbor not in visited:
                                visited.add(neighbor)
                                next_frontier.add(neighbor)
                    frontier = next_frontier
                node_ids = visited
            else:
                node_ids = set(self._players.keys())

            nodes = [
                {"player_id": pid, "display_name": self._players[pid].display_name,
                 "skill_rating": self._players[pid].skill_rating}
                for pid in node_ids if pid in self._players
            ]
            edges = [
                {"edge_id": e.edge_id, "source": e.source_player,
                 "target": e.target_player, "relation": e.relation.value,
                 "strength": e.strength}
                for e in self._edges.values()
                if e.source_player in node_ids and e.target_player in node_ids
            ]
            return {"nodes": nodes, "edges": edges, "node_count": len(nodes),
                    "edge_count": len(edges)}

    # ------------------------------------------------------------------
    # Social Cluster Detection
    # ------------------------------------------------------------------

    def detect_clusters(self, min_size: int = 3) -> List[SocialCluster]:
        with self._lock:
            self._clusters.clear()
            visited: Set[str] = set()
            clusters: List[SocialCluster] = []

            for start in self._adjacency:
                if start in visited:
                    continue
                component: Set[str] = set()
                queue = [start]
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    component.add(node)
                    for neighbor in self._adjacency.get(node, set()):
                        if neighbor not in visited:
                            queue.append(neighbor)

                if len(component) >= min_size:
                    player_list = list(component)
                    ratings = [self._players[p].skill_rating
                               for p in player_list if p in self._players]
                    avg_skill = sum(ratings) / len(ratings) if ratings else 0.0
                    internal_edges = sum(
                        1 for e in self._edges.values()
                        if e.source_player in component and e.target_player in component
                    )
                    max_possible = len(component) * (len(component) - 1) / 2
                    cohesion = internal_edges / max_possible if max_possible > 0 else 0.0
                    cluster = SocialCluster(
                        cluster_id=_new_id("cls"),
                        player_ids=player_list,
                        cluster_type="friend_group",
                        cohesion_score=cohesion,
                        avg_skill=avg_skill,
                        size=len(component),
                    )
                    self._clusters[cluster.cluster_id] = cluster
                    _evict_fifo_dict(self._clusters, _MAX_CLUSTERS)
                    clusters.append(cluster)
                    self._emit(MultiplayerEventKind.CLUSTER_DETECTED, {
                        "cluster_id": cluster.cluster_id,
                        "size": cluster.size,
                        "cohesion": cohesion,
                    })
            return clusters

    def get_cluster(self, cluster_id: str) -> Optional[SocialCluster]:
        with self._lock:
            return self._clusters.get(cluster_id)

    def list_clusters(self, min_size: int = None, limit: int = 50) -> List[SocialCluster]:
        with self._lock:
            items = list(self._clusters.values())
            if min_size is not None:
                items = [c for c in items if c.size >= min_size]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Matchmaking
    # ------------------------------------------------------------------

    def create_ticket(self, player_ids: List[str],
                      strategy: MatchmakingStrategy = MatchmakingStrategy.SKILL_AND_SOCIAL,
                      desired_roles: List[str] = None,
                      metadata: Dict[str, Any] = None) -> Optional[MatchmakingTicket]:
        with self._lock:
            for pid in player_ids:
                if pid not in self._players:
                    return None
            ratings = [self._players[pid].skill_rating for pid in player_ids]
            avg_rating = sum(ratings) / len(ratings) if ratings else 1000.0
            ticket = MatchmakingTicket(
                ticket_id=_new_id("tkt"),
                player_ids=list(player_ids),
                strategy=strategy,
                desired_roles=desired_roles or [],
                avg_rating=avg_rating,
                metadata=metadata or {},
            )
            self._tickets[ticket.ticket_id] = ticket
            _evict_fifo_dict(self._tickets, _MAX_TICKETS)
            self._emit(MultiplayerEventKind.TICKET_CREATED, {
                "ticket_id": ticket.ticket_id,
                "players": len(player_ids),
                "strategy": strategy.value,
            })
            return ticket

    def get_ticket(self, ticket_id: str) -> Optional[MatchmakingTicket]:
        with self._lock:
            return self._tickets.get(ticket_id)

    def list_tickets(self, status: str = None, limit: int = 50) -> List[MatchmakingTicket]:
        with self._lock:
            items = list(self._tickets.values())
            if status is not None:
                items = [t for t in items if t.status == status]
            return items[-limit:]

    def cancel_ticket(self, ticket_id: str) -> Optional[MatchmakingTicket]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None or ticket.status != "queued":
                return None
            ticket.status = "cancelled"
            self._emit(MultiplayerEventKind.TICKET_CANCELLED, {"ticket_id": ticket_id})
            return ticket

    def find_match(self, ticket_id: str) -> Optional[MatchmakingResult]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None or ticket.status != "queued":
                return None
            queued_tickets = [t for t in self._tickets.values()
                              if t.status == "queued" and t.ticket_id != ticket_id]
            if not queued_tickets:
                return None

            best_match = None
            best_score = float("inf")
            for other in queued_tickets:
                rating_diff = abs(ticket.avg_rating - other.avg_rating)
                social_bonus = 0.0
                if ticket.strategy in (MatchmakingStrategy.SKILL_AND_SOCIAL,
                                       MatchmakingStrategy.SOCIAL_FIRST):
                    shared = 0
                    for p1 in ticket.player_ids:
                        for p2 in other.player_ids:
                            if p2 in self._adjacency.get(p1, set()):
                                shared += 1
                    social_bonus = -shared * 50.0
                if ticket.strategy == MatchmakingStrategy.SOCIAL_FIRST:
                    score = social_bonus + rating_diff * 0.3
                else:
                    score = rating_diff + social_bonus
                if score < best_score:
                    best_score = score
                    best_match = other

            if best_match is None:
                return None

            all_players = ticket.player_ids + best_match.player_ids
            if len(all_players) < 2:
                return None
            mid = len(all_players) // 2
            team_a_ids = all_players[:mid]
            team_b_ids = all_players[mid:]

            team_a = self._compose_team_internal(team_a_ids)
            team_b = self._compose_team_internal(team_b_ids)

            match = MatchResult(
                match_id=_new_id("mtc"),
                ticket_ids=[ticket.ticket_id, best_match.ticket_id],
                team_a=team_a,
                team_b=team_b,
                outcome=MatchOutcome.PENDING,
                started_at=_now(),
            )
            self._matches[match.match_id] = match
            _evict_fifo_dict(self._matches, _MAX_MATCHES)
            ticket.status = "matched"
            ticket.matched_at = _now()
            ticket.match_id = match.match_id
            best_match.status = "matched"
            best_match.matched_at = _now()
            best_match.match_id = match.match_id
            for pid in all_players:
                p = self._players.get(pid)
                if p:
                    p.is_in_match = True
            self._emit(MultiplayerEventKind.MATCH_FOUND, {
                "match_id": match.match_id,
                "team_a_size": len(team_a_ids),
                "team_b_size": len(team_b_ids),
            })
            return match

    def get_match(self, match_id: str) -> Optional[MatchResult]:
        with self._lock:
            return self._matches.get(match_id)

    def list_matches(self, outcome: MatchOutcome = None, limit: int = 50) -> List[MatchResult]:
        with self._lock:
            items = list(self._matches.values())
            if outcome is not None:
                items = [m for m in items if m.outcome == outcome]
            return items[-limit:]

    def _compose_team_internal(self, player_ids: List[str]) -> TeamComposition:
        team_id = _new_id("team")
        ratings = [self._players[pid].skill_rating for pid in player_ids
                   if pid in self._players]
        avg_rating = sum(ratings) / len(ratings) if ratings else 1000.0
        role_assignments: Dict[str, str] = {}
        for pid in player_ids:
            player = self._players.get(pid)
            if player and player.preferred_roles:
                role_assignments[pid] = player.preferred_roles[0]
            else:
                role_assignments[pid] = TeamRole.UNASSIGNED.value
        internal_edges = 0
        for i, p1 in enumerate(player_ids):
            for p2 in player_ids[i+1:]:
                if p2 in self._adjacency.get(p1, set()):
                    internal_edges += 1
        max_possible = len(player_ids) * (len(player_ids) - 1) / 2
        cohesion = internal_edges / max_possible if max_possible > 0 else 0.0
        balance = 1.0 - (max(ratings) - min(ratings)) / 1000.0 if ratings else 0.0
        balance = max(0.0, min(1.0, balance))
        return TeamComposition(
            team_id=team_id,
            player_ids=list(player_ids),
            role_assignments=role_assignments,
            avg_rating=avg_rating,
            balance_score=balance,
            social_cohesion=cohesion,
        )

    def compose_teams(self, player_ids: List[str], num_teams: int = 2) -> List[TeamComposition]:
        with self._lock:
            valid_ids = [pid for pid in player_ids if pid in self._players]
            if len(valid_ids) < num_teams:
                return []
            valid_ids.sort(key=lambda pid: self._players[pid].skill_rating, reverse=True)
            teams: List[List[str]] = [[] for _ in range(num_teams)]
            team_sums = [0.0] * num_teams
            for pid in valid_ids:
                weakest_team = team_sums.index(min(team_sums))
                teams[weakest_team].append(pid)
                team_sums[weakest_team] += self._players[pid].skill_rating
            composed = [self._compose_team_internal(team) for team in teams if team]
            self._emit(MultiplayerEventKind.TEAMS_COMPOSED, {
                "num_teams": len(composed),
                "total_players": len(valid_ids),
            })
            return composed

    # ------------------------------------------------------------------
    # Match Results
    # ------------------------------------------------------------------

    def record_result(self, match_id: str, outcome: MatchOutcome,
                      score_team_a: int = 0, score_team_b: int = 0,
                      duration_seconds: int = 0, mvp_player_id: str = "",
                      metadata: Dict[str, Any] = None) -> Optional[MatchResult]:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None or match.outcome != MatchOutcome.PENDING:
                return None
            match.outcome = outcome
            match.score_team_a = score_team_a
            match.score_team_b = score_team_b
            match.duration_seconds = duration_seconds
            match.mvp_player_id = mvp_player_id
            match.completed_at = _now()
            match.metadata = metadata or {}

            team_a_won = outcome == MatchOutcome.TEAM_A_WIN
            team_b_won = outcome == MatchOutcome.TEAM_B_WIN
            is_draw = outcome == MatchOutcome.DRAW

            adjustments: Dict[str, float] = {}
            for pid in match.team_a.player_ids:
                player = self._players.get(pid)
                if player is None:
                    continue
                delta = 0.0
                if team_a_won:
                    delta = 25.0
                    player.wins += 1
                    player.current_streak = max(1, player.current_streak + 1)
                elif team_b_won:
                    delta = -25.0
                    player.losses += 1
                    player.current_streak = min(-1, player.current_streak - 1)
                elif is_draw:
                    delta = 0.0
                player.skill_rating = max(0, player.skill_rating + delta)
                player.total_matches += 1
                player.last_match_at = _now()
                player.is_in_match = False
                adjustments[pid] = delta
                self._recalc_profile(player)

            for pid in match.team_b.player_ids:
                player = self._players.get(pid)
                if player is None:
                    continue
                delta = 0.0
                if team_b_won:
                    delta = 25.0
                    player.wins += 1
                    player.current_streak = max(1, player.current_streak + 1)
                elif team_a_won:
                    delta = -25.0
                    player.losses += 1
                    player.current_streak = min(-1, player.current_streak - 1)
                elif is_draw:
                    delta = 0.0
                player.skill_rating = max(0, player.skill_rating + delta)
                player.total_matches += 1
                player.last_match_at = _now()
                player.is_in_match = False
                adjustments[pid] = delta
                self._recalc_profile(player)

            match.skill_adjustments = adjustments
            self._emit(MultiplayerEventKind.MATCH_COMPLETED, {
                "match_id": match_id,
                "outcome": outcome.value,
            })
            return match

    def list_results(self, player_id: str = None, outcome: MatchOutcome = None,
                     limit: int = 50) -> List[MatchResult]:
        with self._lock:
            items = list(self._matches.values())
            items = [m for m in items if m.outcome != MatchOutcome.PENDING]
            if player_id is not None:
                items = [m for m in items
                         if player_id in m.team_a.player_ids or player_id in m.team_b.player_ids]
            if outcome is not None:
                items = [m for m in items if m.outcome == outcome]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Social Events
    # ------------------------------------------------------------------

    def create_social_event(self, name: str,
                            event_type: SocialEventType = SocialEventType.TOURNAMENT,
                            description: str = "", max_participants: int = 100,
                            min_skill_rating: float = 0.0,
                            max_skill_rating: float = 9999.0,
                            start_time: str = "", end_time: str = "",
                            prize_pool: str = "", rules: str = "") -> SocialEvent:
        with self._lock:
            event = SocialEvent(
                event_id=_new_id("sev"),
                name=name,
                event_type=event_type,
                description=description,
                max_participants=max_participants,
                min_skill_rating=min_skill_rating,
                max_skill_rating=max_skill_rating,
                start_time=start_time,
                end_time=end_time,
                prize_pool=prize_pool,
                rules=rules,
            )
            self._social_events[event.event_id] = event
            _evict_fifo_dict(self._social_events, _MAX_SOCIAL_EVENTS)
            self._emit(MultiplayerEventKind.SOCIAL_EVENT_CREATED, {
                "event_id": event.event_id,
                "event_type": event_type.value,
            })
            return event

    def update_social_event(self, event_id: str, updates: Dict[str, Any]) -> Optional[SocialEvent]:
        with self._lock:
            event = self._social_events.get(event_id)
            if event is None:
                return None
            for k, v in updates.items():
                if k == "event_type" and isinstance(v, str):
                    try:
                        v = SocialEventType(v)
                    except ValueError:
                        continue
                if k == "status" and isinstance(v, str):
                    try:
                        v = EventStatus(v)
                    except ValueError:
                        continue
                if hasattr(event, k) and k not in ("event_id", "created_at"):
                    setattr(event, k, v)
            event.updated_at = _now()
            self._emit(MultiplayerEventKind.SOCIAL_EVENT_LAUNCHED, {"event_id": event_id})
            return event

    def get_social_event(self, event_id: str) -> Optional[SocialEvent]:
        with self._lock:
            return self._social_events.get(event_id)

    def list_social_events(self, status: EventStatus = None,
                           event_type: SocialEventType = None,
                           limit: int = 50) -> List[SocialEvent]:
        with self._lock:
            items = list(self._social_events.values())
            if status is not None:
                items = [e for e in items if e.status == status]
            if event_type is not None:
                items = [e for e in items if e.event_type == event_type]
            return items[-limit:]

    def register_for_event(self, event_id: str, player_id: str) -> Optional[SocialEvent]:
        with self._lock:
            event = self._social_events.get(event_id)
            if event is None:
                return None
            if player_id not in self._players:
                return None
            if len(event.participant_ids) >= event.max_participants:
                return None
            player = self._players[player_id]
            if player.skill_rating < event.min_skill_rating:
                return None
            if player.skill_rating > event.max_skill_rating:
                return None
            if player_id not in event.participant_ids:
                event.participant_ids.append(player_id)
                event.updated_at = _now()
            return event

    def launch_social_event(self, event_id: str) -> Optional[SocialEvent]:
        with self._lock:
            event = self._social_events.get(event_id)
            if event is None:
                return None
            event.status = EventStatus.IN_PROGRESS
            event.start_time = event.start_time or _now()
            event.updated_at = _now()
            self._emit(MultiplayerEventKind.SOCIAL_EVENT_LAUNCHED, {"event_id": event_id})
            return event

    def complete_social_event(self, event_id: str) -> Optional[SocialEvent]:
        with self._lock:
            event = self._social_events.get(event_id)
            if event is None:
                return None
            event.status = EventStatus.COMPLETED
            event.end_time = event.end_time or _now()
            event.updated_at = _now()
            self._emit(MultiplayerEventKind.SOCIAL_EVENT_COMPLETED, {"event_id": event_id})
            return event

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: MultiplayerEventKind = None, limit: int = 100) -> List[MultiplayerEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                items = [e for e in items if e.kind == kind]
            return items[-limit:]

    def get_stats(self) -> MultiplayerStats:
        with self._lock:
            online = sum(1 for p in self._players.values() if p.is_online)
            in_match = sum(1 for p in self._players.values() if p.is_in_match)
            queued = sum(1 for t in self._tickets.values() if t.status == "queued")
            completed = sum(1 for m in self._matches.values()
                            if m.outcome != MatchOutcome.PENDING)
            active_events = sum(1 for e in self._social_events.values()
                                if e.status == EventStatus.IN_PROGRESS)
            return MultiplayerStats(
                total_players=len(self._players),
                online_players=online,
                in_match_players=in_match,
                total_relations=len(self._edges),
                total_clusters=len(self._clusters),
                total_tickets=len(self._tickets),
                queued_tickets=queued,
                total_matches=len(self._matches),
                completed_matches=completed,
                total_results=completed,
                total_social_events=len(self._social_events),
                active_social_events=active_events,
                total_events=len(self._events),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "players": len(self._players),
                "relations": len(self._edges),
                "clusters": len(self._clusters),
                "tickets": len(self._tickets),
                "matches": len(self._matches),
                "social_events": len(self._social_events),
                "events": len(self._events),
            }

    def get_snapshot(self) -> MultiplayerSnapshot:
        with self._lock:
            return MultiplayerSnapshot(
                players=[p.to_dict() for p in list(self._players.values())[:20]],
                clusters=[c.to_dict() for c in list(self._clusters.values())[:20]],
                tickets=[t.to_dict() for t in list(self._tickets.values())[:20]],
                matches=[m.to_dict() for m in list(self._matches.values())[:20]],
                social_events=[e.to_dict() for e in list(self._social_events.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._players.clear()
            self._edges.clear()
            self._adjacency.clear()
            self._clusters.clear()
            self._tickets.clear()
            self._matches.clear()
            self._social_events.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        players_data = [
            ("mp_player_1", "AceStriker", 1850, True, ["dps"]),
            ("mp_player_2", "ShieldMaiden", 1650, True, ["tank"]),
            ("mp_player_3", "HealBot", 1550, True, ["support"]),
            ("mp_player_4", "SniperKing", 1750, True, ["dps"]),
            ("mp_player_5", "FlexMaster", 1450, False, ["flex"]),
            ("mp_player_6", "RookieRanger", 1100, True, ["dps"]),
            ("mp_player_7", "VeteranKnight", 2100, False, ["tank", "leader"]),
        ]
        for pid, name, rating, online, roles in players_data:
            player = SkillProfile(
                player_id=pid,
                display_name=name,
                skill_rating=rating,
                preferred_roles=roles,
                is_online=online,
            )
            self._recalc_profile(player)
            self._players[pid] = player
            self._adjacency[pid] = set()

        relations = [
            ("mp_player_1", "mp_player_2", SocialRelation.FRIEND),
            ("mp_player_1", "mp_player_3", SocialRelation.FRIEND),
            ("mp_player_2", "mp_player_3", SocialRelation.FRIEND),
            ("mp_player_1", "mp_player_4", SocialRelation.RIVAL),
            ("mp_player_5", "mp_player_6", SocialRelation.FRIEND),
            ("mp_player_6", "mp_player_7", SocialRelation.MENTEE),
        ]
        for source, target, rel in relations:
            edge = SocialEdge(
                edge_id=_new_id("edge"),
                source_player=source,
                target_player=target,
                relation=rel,
                strength=0.8,
            )
            self._edges[edge.edge_id] = edge
            self._adjacency[source].add(target)
            self._adjacency[target].add(source)

        tournament = SocialEvent(
            event_id="sev_seed_tourney",
            name="Weekly Skirmish Cup",
            event_type=SocialEventType.TOURNAMENT,
            description="Weekly community tournament open to all skill levels",
            status=EventStatus.REGISTRATION_OPEN,
            max_participants=64,
            min_skill_rating=1000,
            max_skill_rating=9999,
            prize_pool="5000 gems + exclusive skin",
        )
        self._social_events[tournament.event_id] = tournament


# Forward declaration for type hints in find_match
MatchmakingResult = MatchResult


def get_multiplayer_social_director() -> MultiplayerSocialDirector:
    """Factory function returning the singleton MultiplayerSocialDirector instance."""
    return MultiplayerSocialDirector.get_instance()
