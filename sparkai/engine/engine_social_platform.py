"""
SparkLabs Engine - Social Platform Layer

Provides the social platform layer for multiplayer games: friends lists,
parties, clans, lobbies, invites, and player presence. This is the social
graph layer that Steam, PlayStation Network, and Xbox Live expose.

Architecture:
  SocialPlatformSystem (singleton)
    |-- FriendRecord, Party, Clan, Lobby, Invite, PresenceState,
        SocialPlatformStats, SocialPlatformSnapshot, SocialPlatformEvent
    |-- FriendStatus, PartyType, ClanRole, LobbyState, InviteStatus,
        InviteType, PresenceType, SocialPlatformEventKind

Core Capabilities:
  - add_friend / remove_friend / get_friend / list_friends /
    block_player / unblock_player: friend and block list management.
  - create_party / get_party / list_parties / disband_party /
    invite_to_party / kick_from_party: party lifecycle.
  - create_clan / update_clan / get_clan / list_clans / disband_clan /
    invite_to_clan / kick_from_clan / set_clan_role: clan management.
  - create_lobby / get_lobby / list_lobbies / delete_lobby /
    join_lobby / leave_lobby / set_lobby_state: lobby lifecycle.
  - send_invite / accept_invite / decline_invite / get_invite /
    list_invites: cross-system invite workflow.
  - update_presence / get_presence: player online status tracking.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`SocialPlatformSystem.get_instance` or the module-level
:func:`get_social_platform_system` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_FRIENDS: int = 10000
_MAX_PARTIES: int = 2000
_MAX_CLANS: int = 500
_MAX_LOBBIES: int = 1000
_MAX_INVITES: int = 5000
_MAX_PRESENCES: int = 10000
_MAX_EVENTS: int = 5000
_MAX_BLOCKED: int = 5000


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
    if isinstance(value, (set, frozenset)):
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


class FriendStatus(Enum):
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"
    IN_GAME = "in_game"
    IN_PARTY = "in_party"


class PartyType(Enum):
    OPEN = "open"
    CLOSED = "closed"
    INVITE_ONLY = "invite_only"


class ClanRole(Enum):
    LEADER = "leader"
    OFFICER = "officer"
    MEMBER = "member"
    RECRUIT = "recruit"


class LobbyState(Enum):
    LOBBY = "lobby"
    MATCHMAKING = "matchmaking"
    IN_GAME = "in_game"
    POST_GAME = "post_game"
    CLOSED = "closed"


class InviteStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


class InviteType(Enum):
    FRIEND = "friend"
    PARTY = "party"
    CLAN = "clan"
    LOBBY = "lobby"


class PresenceType(Enum):
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"
    IN_GAME = "in_game"


class SocialPlatformEventKind(Enum):
    FRIEND_ADDED = "friend_added"
    FRIEND_REMOVED = "friend_removed"
    PLAYER_BLOCKED = "player_blocked"
    PLAYER_UNBLOCKED = "player_unblocked"
    PARTY_CREATED = "party_created"
    PARTY_DISBANDED = "party_disbanded"
    PARTY_MEMBER_JOINED = "party_member_joined"
    PARTY_MEMBER_LEFT = "party_member_left"
    CLAN_CREATED = "clan_created"
    CLAN_DISBANDED = "clan_disbanded"
    CLAN_MEMBER_JOINED = "clan_member_joined"
    CLAN_MEMBER_LEFT = "clan_member_left"
    CLAN_ROLE_CHANGED = "clan_role_changed"
    LOBBY_CREATED = "lobby_created"
    LOBBY_DELETED = "lobby_deleted"
    LOBBY_PLAYER_JOINED = "lobby_player_joined"
    LOBBY_PLAYER_LEFT = "lobby_player_left"
    INVITE_SENT = "invite_sent"
    INVITE_ACCEPTED = "invite_accepted"
    INVITE_DECLINED = "invite_declined"
    PRESENCE_UPDATED = "presence_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class FriendRecord:
    """A friend relationship between two players."""
    record_id: str
    player_id: str
    friend_id: str
    display_name: str = ""
    status: FriendStatus = FriendStatus.OFFLINE
    current_game: str = ""
    added_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Party:
    """A temporary group of players."""
    party_id: str
    leader_id: str
    party_type: PartyType = PartyType.INVITE_ONLY
    max_members: int = 5
    member_ids: List[str] = field(default_factory=list)
    game_id: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Clan:
    """A persistent player organization."""
    clan_id: str
    name: str
    leader_id: str = ""
    description: str = ""
    tag: str = ""
    member_ids: List[str] = field(default_factory=list)
    officer_ids: List[str] = field(default_factory=list)
    max_members: int = 50
    is_recruiting: bool = True
    level: int = 1
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Lobby:
    """A pre-game gathering space."""
    lobby_id: str
    host_id: str
    game_mode: str = ""
    max_players: int = 8
    player_ids: List[str] = field(default_factory=list)
    state: LobbyState = LobbyState.LOBBY
    password: str = ""
    region: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Invite:
    """An invitation to a friend/party/clan/lobby."""
    invite_id: str
    invite_type: InviteType = InviteType.FRIEND
    sender_id: str = ""
    recipient_id: str = ""
    target_id: str = ""
    status: InviteStatus = InviteStatus.PENDING
    message: str = ""
    expires_at: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PresenceState:
    """A player's presence information."""
    player_id: str
    presence: PresenceType = PresenceType.OFFLINE
    current_game: str = ""
    current_activity: str = ""
    status_message: str = ""
    last_seen: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocialPlatformStats:
    """Aggregate statistics for the social platform."""
    total_friends: int = 0
    total_parties: int = 0
    total_clans: int = 0
    total_lobbies: int = 0
    total_invites: int = 0
    pending_invites: int = 0
    online_players: int = 0
    total_blocked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocialPlatformSnapshot:
    """Point-in-time snapshot of the social platform."""
    friends: int = 0
    parties: int = 0
    clans: int = 0
    lobbies: int = 0
    invites: int = 0
    presences: int = 0
    blocked: int = 0
    stats: SocialPlatformStats = field(default_factory=SocialPlatformStats)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocialPlatformEvent:
    """An event in the social platform."""
    event_id: str
    kind: SocialPlatformEventKind
    timestamp: str = field(default_factory=_now)
    player_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Social Platform System (Singleton)
# ---------------------------------------------------------------------------


class SocialPlatformSystem:
    """Social platform layer with friends, parties, clans, lobbies,
    invites, and player presence."""

    _instance: Optional["SocialPlatformSystem"] = None
    _inner_lock = threading.RLock()

    def __new__(cls) -> "SocialPlatformSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._friends: Dict[str, FriendRecord] = {}
            self._parties: Dict[str, Party] = {}
            self._clans: Dict[str, Clan] = {}
            self._lobbies: Dict[str, Lobby] = {}
            self._invites: Dict[str, Invite] = {}
            self._presences: Dict[str, PresenceState] = {}
            self._blocked: Dict[str, Set[str]] = {}
            self._events: List[SocialPlatformEvent] = []
            self._initialized = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        # Seed a clan
        clan = Clan(
            clan_id="clan_seed_iron",
            name="Iron Wolves",
            leader_id="player_social_1",
            description="A clan of seasoned warriors.",
            tag="IRW",
            member_ids=["player_social_1", "player_social_2", "player_social_3"],
            officer_ids=["player_social_2"],
            level=10,
        )
        self._clans[clan.clan_id] = clan

        # Seed a party
        party = Party(
            party_id="pty_seed_1",
            leader_id="player_social_1",
            party_type=PartyType.OPEN,
            member_ids=["player_social_1", "player_social_2"],
            game_id="spark_arena",
        )
        self._parties[party.party_id] = party

        # Seed a lobby
        lobby = Lobby(
            lobby_id="lby_seed_1",
            host_id="player_social_1",
            game_mode="ranked",
            max_players=6,
            player_ids=["player_social_1", "player_social_2", "player_social_3"],
            state=LobbyState.LOBBY,
            region="na",
        )
        self._lobbies[lobby.lobby_id] = lobby

        # Seed presences
        for pid in ["player_social_1", "player_social_2", "player_social_3"]:
            self._presences[pid] = PresenceState(
                player_id=pid,
                presence=PresenceType.IN_GAME,
                current_game="spark_arena",
                current_activity="in_match",
            )

    # ------------------------------------------------------------------
    # Friends
    # ------------------------------------------------------------------

    def add_friend(
        self, player_id: str, friend_id: str, display_name: str = ""
    ) -> FriendRecord:
        with self._lock:
            record = FriendRecord(
                record_id=_new_id("fr"),
                player_id=player_id,
                friend_id=friend_id,
                display_name=display_name,
            )
            self._friends[record.record_id] = record
            _evict_fifo_dict(self._friends, _MAX_FRIENDS)
            self._emit(SocialPlatformEventKind.FRIEND_ADDED, {
                "player_id": player_id, "friend_id": friend_id,
            })
            return record

    def remove_friend(self, record_id: str) -> bool:
        with self._lock:
            rec = self._friends.pop(record_id, None)
            if rec is not None:
                self._emit(SocialPlatformEventKind.FRIEND_REMOVED, {
                    "player_id": rec.player_id, "friend_id": rec.friend_id,
                })
            return rec is not None

    def get_friend(self, record_id: str) -> Optional[FriendRecord]:
        with self._lock:
            return self._friends.get(record_id)

    def list_friends(
        self, player_id: Optional[str] = None, status: Optional[FriendStatus] = None,
        limit: int = 100,
    ) -> List[FriendRecord]:
        with self._lock:
            items = list(self._friends.values())
            if player_id:
                items = [f for f in items if f.player_id == player_id]
            if status:
                items = [f for f in items if f.status == status]
            return items[:limit]

    def block_player(self, player_id: str, blocked_id: str) -> bool:
        with self._lock:
            if player_id not in self._blocked:
                self._blocked[player_id] = set()
            if blocked_id in self._blocked[player_id]:
                return False
            self._blocked[player_id].add(blocked_id)
            self._emit(SocialPlatformEventKind.PLAYER_BLOCKED, {
                "player_id": player_id, "blocked_id": blocked_id,
            })
            return True

    def unblock_player(self, player_id: str, blocked_id: str) -> bool:
        with self._lock:
            if player_id in self._blocked:
                if blocked_id in self._blocked[player_id]:
                    self._blocked[player_id].discard(blocked_id)
                    self._emit(SocialPlatformEventKind.PLAYER_UNBLOCKED, {
                        "player_id": player_id, "blocked_id": blocked_id,
                    })
                    return True
            return False

    def list_blocked(self, player_id: str) -> List[str]:
        with self._lock:
            return list(self._blocked.get(player_id, set()))

    # ------------------------------------------------------------------
    # Parties
    # ------------------------------------------------------------------

    def create_party(
        self, leader_id: str, party_type: PartyType = PartyType.INVITE_ONLY,
        max_members: int = 5, game_id: str = "",
    ) -> Party:
        with self._lock:
            party = Party(
                party_id=_new_id("pty"),
                leader_id=leader_id,
                party_type=party_type,
                max_members=max_members,
                member_ids=[leader_id],
                game_id=game_id,
            )
            self._parties[party.party_id] = party
            _evict_fifo_dict(self._parties, _MAX_PARTIES)
            self._emit(SocialPlatformEventKind.PARTY_CREATED, {
                "party_id": party.party_id, "leader_id": leader_id,
            })
            return party

    def get_party(self, party_id: str) -> Optional[Party]:
        with self._lock:
            return self._parties.get(party_id)

    def list_parties(
        self, leader_id: Optional[str] = None, game_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Party]:
        with self._lock:
            items = list(self._parties.values())
            if leader_id:
                items = [p for p in items if p.leader_id == leader_id]
            if game_id:
                items = [p for p in items if p.game_id == game_id]
            return items[:limit]

    def invite_to_party(self, party_id: str, player_id: str) -> Optional[Party]:
        with self._lock:
            party = self._parties.get(party_id)
            if party is None:
                return None
            if len(party.member_ids) >= party.max_members:
                return None
            if player_id not in party.member_ids:
                party.member_ids.append(player_id)
                party.updated_at = _now()
                self._emit(SocialPlatformEventKind.PARTY_MEMBER_JOINED, {
                    "party_id": party_id, "player_id": player_id,
                })
            return party

    def kick_from_party(self, party_id: str, player_id: str) -> Optional[Party]:
        with self._lock:
            party = self._parties.get(party_id)
            if party is None:
                return None
            if player_id in party.member_ids:
                party.member_ids.remove(player_id)
                party.updated_at = _now()
                self._emit(SocialPlatformEventKind.PARTY_MEMBER_LEFT, {
                    "party_id": party_id, "player_id": player_id,
                })
            return party

    def disband_party(self, party_id: str) -> bool:
        with self._lock:
            party = self._parties.pop(party_id, None)
            if party is not None:
                self._emit(SocialPlatformEventKind.PARTY_DISBANDED, {
                    "party_id": party_id,
                })
            return party is not None

    # ------------------------------------------------------------------
    # Clans
    # ------------------------------------------------------------------

    def create_clan(
        self, name: str, leader_id: str = "", description: str = "",
        tag: str = "", max_members: int = 50,
    ) -> Clan:
        with self._lock:
            clan = Clan(
                clan_id=_new_id("clan"),
                name=name,
                leader_id=leader_id,
                description=description,
                tag=tag,
                max_members=max_members,
                member_ids=[leader_id] if leader_id else [],
            )
            self._clans[clan.clan_id] = clan
            _evict_fifo_dict(self._clans, _MAX_CLANS)
            self._emit(SocialPlatformEventKind.CLAN_CREATED, {
                "clan_id": clan.clan_id, "name": name,
            })
            return clan

    def update_clan(
        self, clan_id: str, name: Optional[str] = None,
        description: Optional[str] = None, tag: Optional[str] = None,
        is_recruiting: Optional[bool] = None, level: Optional[int] = None,
    ) -> Optional[Clan]:
        with self._lock:
            clan = self._clans.get(clan_id)
            if clan is None:
                return None
            if name is not None:
                clan.name = name
            if description is not None:
                clan.description = description
            if tag is not None:
                clan.tag = tag
            if is_recruiting is not None:
                clan.is_recruiting = is_recruiting
            if level is not None:
                clan.level = level
            clan.updated_at = _now()
            return clan

    def get_clan(self, clan_id: str) -> Optional[Clan]:
        with self._lock:
            return self._clans.get(clan_id)

    def list_clans(
        self, is_recruiting: Optional[bool] = None, limit: int = 50
    ) -> List[Clan]:
        with self._lock:
            items = list(self._clans.values())
            if is_recruiting is not None:
                items = [c for c in items if c.is_recruiting == is_recruiting]
            return items[:limit]

    def invite_to_clan(self, clan_id: str, player_id: str) -> Optional[Clan]:
        with self._lock:
            clan = self._clans.get(clan_id)
            if clan is None:
                return None
            if len(clan.member_ids) >= clan.max_members:
                return None
            if player_id not in clan.member_ids:
                clan.member_ids.append(player_id)
                clan.updated_at = _now()
                self._emit(SocialPlatformEventKind.CLAN_MEMBER_JOINED, {
                    "clan_id": clan_id, "player_id": player_id,
                })
            return clan

    def kick_from_clan(self, clan_id: str, player_id: str) -> Optional[Clan]:
        with self._lock:
            clan = self._clans.get(clan_id)
            if clan is None:
                return None
            if player_id in clan.member_ids:
                clan.member_ids.remove(player_id)
                if player_id in clan.officer_ids:
                    clan.officer_ids.remove(player_id)
                clan.updated_at = _now()
                self._emit(SocialPlatformEventKind.CLAN_MEMBER_LEFT, {
                    "clan_id": clan_id, "player_id": player_id,
                })
            return clan

    def set_clan_role(
        self, clan_id: str, player_id: str, role: ClanRole
    ) -> Optional[Clan]:
        with self._lock:
            clan = self._clans.get(clan_id)
            if clan is None:
                return None
            if player_id not in clan.member_ids:
                return None
            if role == ClanRole.OFFICER and player_id not in clan.officer_ids:
                clan.officer_ids.append(player_id)
            elif role == ClanRole.MEMBER and player_id in clan.officer_ids:
                clan.officer_ids.remove(player_id)
            clan.updated_at = _now()
            self._emit(SocialPlatformEventKind.CLAN_ROLE_CHANGED, {
                "clan_id": clan_id, "player_id": player_id, "role": role.value,
            })
            return clan

    def disband_clan(self, clan_id: str) -> bool:
        with self._lock:
            clan = self._clans.pop(clan_id, None)
            if clan is not None:
                self._emit(SocialPlatformEventKind.CLAN_DISBANDED, {
                    "clan_id": clan_id,
                })
            return clan is not None

    # ------------------------------------------------------------------
    # Lobbies
    # ------------------------------------------------------------------

    def create_lobby(
        self, host_id: str, game_mode: str = "", max_players: int = 8,
        region: str = "", password: str = "",
    ) -> Lobby:
        with self._lock:
            lobby = Lobby(
                lobby_id=_new_id("lby"),
                host_id=host_id,
                game_mode=game_mode,
                max_players=max_players,
                player_ids=[host_id],
                region=region,
                password=password,
            )
            self._lobbies[lobby.lobby_id] = lobby
            _evict_fifo_dict(self._lobbies, _MAX_LOBBIES)
            self._emit(SocialPlatformEventKind.LOBBY_CREATED, {
                "lobby_id": lobby.lobby_id, "host_id": host_id,
            })
            return lobby

    def get_lobby(self, lobby_id: str) -> Optional[Lobby]:
        with self._lock:
            return self._lobbies.get(lobby_id)

    def list_lobbies(
        self, state: Optional[LobbyState] = None, game_mode: Optional[str] = None,
        limit: int = 50,
    ) -> List[Lobby]:
        with self._lock:
            items = list(self._lobbies.values())
            if state:
                items = [l for l in items if l.state == state]
            if game_mode:
                items = [l for l in items if l.game_mode == game_mode]
            return items[:limit]

    def join_lobby(self, lobby_id: str, player_id: str) -> Optional[Lobby]:
        with self._lock:
            lobby = self._lobbies.get(lobby_id)
            if lobby is None:
                return None
            if len(lobby.player_ids) >= lobby.max_players:
                return None
            if player_id not in lobby.player_ids:
                lobby.player_ids.append(player_id)
                lobby.updated_at = _now()
                self._emit(SocialPlatformEventKind.LOBBY_PLAYER_JOINED, {
                    "lobby_id": lobby_id, "player_id": player_id,
                })
            return lobby

    def leave_lobby(self, lobby_id: str, player_id: str) -> Optional[Lobby]:
        with self._lock:
            lobby = self._lobbies.get(lobby_id)
            if lobby is None:
                return None
            if player_id in lobby.player_ids:
                lobby.player_ids.remove(player_id)
                lobby.updated_at = _now()
                self._emit(SocialPlatformEventKind.LOBBY_PLAYER_LEFT, {
                    "lobby_id": lobby_id, "player_id": player_id,
                })
            return lobby

    def set_lobby_state(
        self, lobby_id: str, state: LobbyState
    ) -> Optional[Lobby]:
        with self._lock:
            lobby = self._lobbies.get(lobby_id)
            if lobby is None:
                return None
            lobby.state = state
            lobby.updated_at = _now()
            return lobby

    def delete_lobby(self, lobby_id: str) -> bool:
        with self._lock:
            lobby = self._lobbies.pop(lobby_id, None)
            if lobby is not None:
                self._emit(SocialPlatformEventKind.LOBBY_DELETED, {
                    "lobby_id": lobby_id,
                })
            return lobby is not None

    # ------------------------------------------------------------------
    # Invites
    # ------------------------------------------------------------------

    def send_invite(
        self, sender_id: str, recipient_id: str, invite_type: InviteType,
        target_id: str = "", message: str = "",
    ) -> Invite:
        with self._lock:
            invite = Invite(
                invite_id=_new_id("inv"),
                invite_type=invite_type,
                sender_id=sender_id,
                recipient_id=recipient_id,
                target_id=target_id,
                message=message,
            )
            self._invites[invite.invite_id] = invite
            _evict_fifo_dict(self._invites, _MAX_INVITES)
            self._emit(SocialPlatformEventKind.INVITE_SENT, {
                "invite_id": invite.invite_id, "recipient_id": recipient_id,
            })
            return invite

    def accept_invite(self, invite_id: str) -> Optional[Invite]:
        with self._lock:
            invite = self._invites.get(invite_id)
            if invite is None or invite.status != InviteStatus.PENDING:
                return None
            invite.status = InviteStatus.ACCEPTED
            self._emit(SocialPlatformEventKind.INVITE_ACCEPTED, {
                "invite_id": invite_id,
            })
            return invite

    def decline_invite(self, invite_id: str) -> Optional[Invite]:
        with self._lock:
            invite = self._invites.get(invite_id)
            if invite is None or invite.status != InviteStatus.PENDING:
                return None
            invite.status = InviteStatus.DECLINED
            self._emit(SocialPlatformEventKind.INVITE_DECLINED, {
                "invite_id": invite_id,
            })
            return invite

    def get_invite(self, invite_id: str) -> Optional[Invite]:
        with self._lock:
            return self._invites.get(invite_id)

    def list_invites(
        self, recipient_id: Optional[str] = None, status: Optional[InviteStatus] = None,
        invite_type: Optional[InviteType] = None, limit: int = 50,
    ) -> List[Invite]:
        with self._lock:
            items = list(self._invites.values())
            if recipient_id:
                items = [i for i in items if i.recipient_id == recipient_id]
            if status:
                items = [i for i in items if i.status == status]
            if invite_type:
                items = [i for i in items if i.invite_type == invite_type]
            return items[:limit]

    # ------------------------------------------------------------------
    # Presence
    # ------------------------------------------------------------------

    def update_presence(
        self, player_id: str, presence: PresenceType = PresenceType.ONLINE,
        current_game: str = "", current_activity: str = "",
        status_message: str = "",
    ) -> PresenceState:
        with self._lock:
            state = self._presences.get(player_id)
            if state is None:
                state = PresenceState(player_id=player_id)
                self._presences[player_id] = state
            state.presence = presence
            state.current_game = current_game
            state.current_activity = current_activity
            state.status_message = status_message
            state.last_seen = _now()
            state.updated_at = _now()
            self._emit(SocialPlatformEventKind.PRESENCE_UPDATED, {
                "player_id": player_id, "presence": presence.value,
            })
            return state

    def get_presence(self, player_id: str) -> Optional[PresenceState]:
        with self._lock:
            return self._presences.get(player_id)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _emit(self, kind: SocialPlatformEventKind, data: Dict[str, Any]) -> None:
        event = SocialPlatformEvent(
            event_id=_new_id("evt"),
            kind=kind,
            player_id=data.get("player_id", ""),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(
        self, kind: Optional[SocialPlatformEventKind] = None, limit: int = 100
    ) -> List[SocialPlatformEvent]:
        with self._lock:
            items = self._events
            if kind:
                items = [e for e in items if e.kind == kind]
            return list(items[:limit])

    def get_stats(self) -> SocialPlatformStats:
        with self._lock:
            pending = sum(1 for i in self._invites.values() if i.status == InviteStatus.PENDING)
            online = sum(1 for p in self._presences.values() if p.presence != PresenceType.OFFLINE)
            blocked_count = sum(len(v) for v in self._blocked.values())
            return SocialPlatformStats(
                total_friends=len(self._friends),
                total_parties=len(self._parties),
                total_clans=len(self._clans),
                total_lobbies=len(self._lobbies),
                total_invites=len(self._invites),
                pending_invites=pending,
                online_players=online,
                total_blocked=blocked_count,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "friends": len(self._friends),
                "parties": len(self._parties),
                "clans": len(self._clans),
                "lobbies": len(self._lobbies),
                "invites": len(self._invites),
                "presences": len(self._presences),
                "blocked": sum(len(v) for v in self._blocked.values()),
                "events": len(self._events),
            }

    def get_snapshot(self) -> SocialPlatformSnapshot:
        with self._lock:
            return SocialPlatformSnapshot(
                friends=len(self._friends),
                parties=len(self._parties),
                clans=len(self._clans),
                lobbies=len(self._lobbies),
                invites=len(self._invites),
                presences=len(self._presences),
                blocked=sum(len(v) for v in self._blocked.values()),
                stats=self.get_stats(),
            )

    def reset(self) -> None:
        with self._lock:
            self._friends.clear()
            self._parties.clear()
            self._clans.clear()
            self._lobbies.clear()
            self._invites.clear()
            self._presences.clear()
            self._blocked.clear()
            self._events.clear()
            self._seed_data()


def get_social_platform_system() -> SocialPlatformSystem:
    """Get the singleton SocialPlatformSystem instance."""
    return SocialPlatformSystem()
