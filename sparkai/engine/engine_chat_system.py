"""
SparkLabs Engine - In-Game Voice & Text Chat System

A comprehensive real-time communication system for the SparkLabs AI-native
game engine. The chat system orchestrates text channels, voice channels,
per-user presence, AI-powered content moderation, and audit logging.
Players can join channels, send text messages, participate in voice chats,
and have their messages filtered by configurable rules. Moderators can
warn, mute, kick, ban, or shadow-mute users who violate policies.

Architecture:
  ChatSystem (singleton)
    |-- ChatChannel         -- a text or voice channel with members
    |-- ChatMessage         -- a single chat message with lifecycle status
    |-- VoiceParticipant    -- a participant in a voice channel session
    |-- ChatFilterRule      -- a moderation filter rule (profanity, spam, etc.)
    |-- ModerationAction    -- a moderation action applied to a user
    |-- ChatUser            -- a registered chat user with presence state
    |-- ChatStats           -- aggregate counters describing chat state
    |-- ChatSnapshot        -- immutable state snapshot
    |-- ChatEvent           -- audit log entry
    |-- ChannelType         -- 9 channel classifications
    |-- MessageStatus       -- 5 message lifecycle states
    |-- FilterCategory      -- 6 filter rule categories
    |-- ModerationActionType -- 6 moderation action types
    |-- UserStatus          -- 5 user presence states
    |-- ChatEventKind       -- audit event kinds

Core Capabilities:
  - create_channel / get_channel / list_channels / delete_channel:
    channel registry with type, members, voice, and slow-mode.
  - join_channel / leave_channel: membership management with voice
    participant tracking for voice channels.
  - send_message / get_message / list_messages / delete_message:
    message lifecycle with content filtering and status tracking.
  - register_user / get_user / update_user_status / list_users:
    user registry with presence and per-channel mute state.
  - create_filter_rule / get_filter_rule / list_filter_rules /
    delete_filter_rule: configurable content moderation rules.
  - moderate_user / list_moderation_actions: moderation enforcement
    with mute, ban, kick, warn, shadow-mute, and filter-message.
  - list_events_log / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CHANNELS: int = 2000
_MAX_MESSAGES: int = 50000
_MAX_USERS: int = 10000
_MAX_FILTER_RULES: int = 500
_MAX_MODERATION_ACTIONS: int = 10000
_MAX_VOICE_PARTICIPANTS: int = 2000
_MAX_MEMBERS_PER_CHANNEL: int = 500
_MAX_MESSAGES_PER_CHANNEL: int = 1000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload."""
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
    """Convert a dataclass instance to a plain dictionary."""
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


class ChannelType(Enum):
    """Classification of chat channels."""

    GLOBAL = "global"
    TEAM = "team"
    GUILD = "guild"
    PARTY = "party"
    WHISPER = "whisper"
    SYSTEM = "system"
    VOICE = "voice"
    TRADE = "trade"
    HELP = "help"


class MessageStatus(Enum):
    """Lifecycle states for chat messages."""

    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    DELETED = "deleted"
    FILTERED = "filtered"


class FilterCategory(Enum):
    """Categories of content filter rules."""

    PROFANITY = "profanity"
    SPAM = "spam"
    TOXICITY = "toxicity"
    PERSONAL_INFO = "personal_info"
    ADVERTISING = "advertising"
    CUSTOM = "custom"


class ModerationActionType(Enum):
    """Types of moderation actions applied to users."""

    WARN = "warn"
    MUTE = "mute"
    KICK = "kick"
    BAN = "ban"
    SHADOW_MUTE = "shadow_mute"
    FILTER_MESSAGE = "filter_message"


class UserStatus(Enum):
    """Presence states for chat users."""

    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"
    VOICE_CHAT = "voice_chat"


class ChatEventKind(Enum):
    """Audit event kinds emitted by the chat system."""

    CHANNEL_CREATED = "channel_created"
    CHANNEL_DELETED = "channel_deleted"
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELETED = "message_deleted"
    MESSAGE_FILTERED = "message_filtered"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_REGISTERED = "user_registered"
    USER_STATUS_UPDATED = "user_status_updated"
    FILTER_RULE_CREATED = "filter_rule_created"
    FILTER_RULE_DELETED = "filter_rule_deleted"
    MODERATION_ACTION = "moderation_action"
    VOICE_PARTICIPANT_JOINED = "voice_participant_joined"
    VOICE_PARTICIPANT_LEFT = "voice_participant_left"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ChatChannel:
    """A text or voice channel with a member roster.

    Attributes:
        channel_id: Unique identifier for the channel.
        name: Display name of the channel.
        channel_type: The ChannelType classification.
        owner_id: The user id who owns the channel.
        description: Human-readable description.
        member_ids: List of user ids currently in the channel.
        voice: Whether this is a voice channel.
        max_members: Maximum number of members allowed.
        slow_mode_seconds: Minimum seconds between messages per user.
        created_at: Timestamp when the channel was created.
        updated_at: Timestamp when the channel was last updated.
        metadata: Free-form metadata bag.
    """

    channel_id: str = field(default_factory=lambda: _new_id("ch"))
    name: str = "Untitled Channel"
    channel_type: ChannelType = ChannelType.GLOBAL
    owner_id: str = ""
    description: str = ""
    member_ids: List[str] = field(default_factory=list)
    voice: bool = False
    max_members: int = _MAX_MEMBERS_PER_CHANNEL
    slow_mode_seconds: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChatMessage:
    """A single chat message with lifecycle status.

    Attributes:
        message_id: Unique identifier for the message.
        channel_id: The channel the message belongs to.
        sender_id: The user id of the sender.
        content: The (possibly filtered) message content.
        status: The current MessageStatus.
        filtered: Whether any filter rule matched this message.
        original_content: The original content if the message was filtered.
        matched_rule_ids: List of filter rule ids that matched.
        mentions: List of user ids mentioned in the message.
        edited: Whether the message was edited.
        edited_at: Timestamp when the message was last edited.
        created_at: Timestamp when the message was sent.
        delivered_at: Timestamp when the message was delivered.
        read_at: Timestamp when the message was read.
        metadata: Free-form metadata bag.
    """

    message_id: str = field(default_factory=lambda: _new_id("msg"))
    channel_id: str = ""
    sender_id: str = ""
    content: str = ""
    status: MessageStatus = MessageStatus.SENT
    filtered: bool = False
    original_content: str = ""
    matched_rule_ids: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    edited: bool = False
    edited_at: str = ""
    created_at: str = field(default_factory=_now)
    delivered_at: str = ""
    read_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceParticipant:
    """A participant in a voice channel session.

    Attributes:
        participant_id: Unique identifier for the voice participant.
        user_id: The user id of the participant.
        channel_id: The voice channel the participant is in.
        muted: Whether the participant's microphone is muted.
        deafened: Whether the participant's audio output is muted.
        speaking: Whether the participant is currently speaking.
        volume: Output volume in [0.0, 1.0].
        push_to_talk: Whether push-to-talk is enabled.
        joined_at: Timestamp when the participant joined the voice channel.
        metadata: Free-form metadata bag.
    """

    participant_id: str = field(default_factory=lambda: _new_id("vp"))
    user_id: str = ""
    channel_id: str = ""
    muted: bool = False
    deafened: bool = False
    speaking: bool = False
    volume: float = 1.0
    push_to_talk: bool = False
    joined_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChatFilterRule:
    """A configurable content moderation rule.

    Attributes:
        rule_id: Unique identifier for the rule.
        name: Display name of the rule.
        category: The FilterCategory classification.
        pattern: Case-insensitive substring pattern to match.
        action: Action to take when the rule matches ("flag", "filter",
            or "block").
        replacement: Optional replacement text for filtered content.
        enabled: Whether the rule is active.
        severity: Severity level from 0 (info) to 3 (critical).
        created_at: Timestamp when the rule was created.
        updated_at: Timestamp when the rule was last updated.
        metadata: Free-form metadata bag.
    """

    rule_id: str = field(default_factory=lambda: _new_id("rule"))
    name: str = "Untitled Rule"
    category: FilterCategory = FilterCategory.CUSTOM
    pattern: str = ""
    action: str = "flag"
    replacement: str = ""
    enabled: bool = True
    severity: int = 1
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ModerationAction:
    """A moderation action applied to a user.

    Attributes:
        action_id: Unique identifier for the action.
        moderator_id: The user id of the moderator.
        target_user_id: The user id of the moderated user.
        action_type: The ModerationActionType.
        channel_id: The channel the action applies to (empty for global).
        reason: Human-readable reason for the action.
        duration_seconds: Duration in seconds (0 means permanent).
        expires_at: ISO timestamp when the action expires (empty if permanent).
        active: Whether the action is currently active.
        created_at: Timestamp when the action was created.
        metadata: Free-form metadata bag.
    """

    action_id: str = field(default_factory=lambda: _new_id("mod"))
    moderator_id: str = ""
    target_user_id: str = ""
    action_type: ModerationActionType = ModerationActionType.WARN
    channel_id: str = ""
    reason: str = ""
    duration_seconds: float = 0.0
    expires_at: str = ""
    active: bool = True
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChatUser:
    """A registered chat user with presence state.

    Attributes:
        user_id: Unique identifier for the user.
        display_name: Display name shown in chat.
        status: The current UserStatus.
        status_message: Optional custom status message.
        channel_ids: List of channel ids the user has joined.
        muted_channels: List of channel ids the user is muted in.
        role: The user role (e.g. "player", "moderator", "admin").
        last_seen: Timestamp when the user was last active.
        created_at: Timestamp when the user was registered.
        updated_at: Timestamp when the user was last updated.
        metadata: Free-form metadata bag.
    """

    user_id: str = field(default_factory=lambda: _new_id("user"))
    display_name: str = "Anonymous"
    status: UserStatus = UserStatus.ONLINE
    status_message: str = ""
    channel_ids: List[str] = field(default_factory=list)
    muted_channels: List[str] = field(default_factory=list)
    role: str = "player"
    last_seen: str = field(default_factory=_now)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChatStats:
    """Aggregate statistics for the chat system.

    Attributes:
        total_channels: Number of channels stored.
        total_messages: Number of messages stored.
        total_users: Number of users registered.
        total_filter_rules: Number of filter rules stored.
        total_moderation_actions: Number of moderation actions stored.
        total_voice_participants: Number of active voice participants.
        active_channels: Number of channels with at least one member.
        messages_sent: Lifetime count of messages sent.
        messages_filtered: Lifetime count of messages filtered.
        active_mutes: Number of currently active mute/ban actions.
        total_events: Number of audit events stored.
        channel_counter: Lifetime count of channels created.
        message_counter: Lifetime count of messages created.
        user_counter: Lifetime count of users registered.
        filter_counter: Lifetime count of filter rules created.
        moderation_counter: Lifetime count of moderation actions applied.
        event_counter: Lifetime count of audit events emitted.
    """

    total_channels: int = 0
    total_messages: int = 0
    total_users: int = 0
    total_filter_rules: int = 0
    total_moderation_actions: int = 0
    total_voice_participants: int = 0
    active_channels: int = 0
    messages_sent: int = 0
    messages_filtered: int = 0
    active_mutes: int = 0
    total_events: int = 0
    channel_counter: int = 0
    message_counter: int = 0
    user_counter: int = 0
    filter_counter: int = 0
    moderation_counter: int = 0
    event_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChatSnapshot:
    """A point-in-time snapshot of the entire chat system state.

    Attributes:
        channels: List of all channels as dicts.
        messages: List of all messages as dicts.
        users: List of all users as dicts.
        filter_rules: List of all filter rules as dicts.
        moderation_actions: List of all moderation actions as dicts.
        voice_participants: List of all voice participants as dicts.
        stats: Aggregate statistics as a dict.
        taken_at: Timestamp when the snapshot was taken.
    """

    channels: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    users: List[Dict[str, Any]] = field(default_factory=list)
    filter_rules: List[Dict[str, Any]] = field(default_factory=list)
    moderation_actions: List[Dict[str, Any]] = field(default_factory=list)
    voice_participants: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChatEvent:
    """An audit event emitted by the chat system.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The ChatEventKind classification.
        timestamp: When the event occurred.
        data: Event-specific payload data.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: ChatEventKind = ChatEventKind.MESSAGE_SENT
    timestamp: str = field(default_factory=_now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Chat System Singleton
# ---------------------------------------------------------------------------


class ChatSystem:
    """Engine-level in-game voice and text chat manager.

    Tracks channels, messages, users, filter rules, moderation actions,
    and voice participants. Implements the singleton pattern with
    double-checked locking for thread-safe access. All public methods
    are guarded by a re-entrant lock.
    """

    _instance: Optional["ChatSystem"] = None
    _inner_lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "ChatSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            # Channels keyed by channel id.
            self._channels: Dict[str, ChatChannel] = {}
            # Messages keyed by message id.
            self._messages: Dict[str, ChatMessage] = {}
            # Users keyed by user id.
            self._users: Dict[str, ChatUser] = {}
            # Filter rules keyed by rule id.
            self._filter_rules: Dict[str, ChatFilterRule] = {}
            # Moderation actions keyed by action id.
            self._moderation_actions: Dict[str, ModerationAction] = {}
            # Voice participants keyed by participant id.
            self._voice_participants: Dict[str, VoiceParticipant] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: List[ChatEvent] = []
            # Aggregate statistics maintained for fast retrieval.
            self._stats = ChatStats()
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: ChatEventKind, data: Dict[str, Any]) -> None:
        """Record an audit event and evict the oldest if over capacity."""
        event = ChatEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        self._stats.event_counter += 1
        self._stats.total_events = len(self._events)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _apply_filters(self, content: str) -> tuple:
        """Apply enabled filter rules to ``content``.

        Returns a tuple of ``(final_content, filtered, matched_rule_ids,
        blocked)``.
        """
        final_content = content
        filtered = False
        blocked = False
        matched_rule_ids: List[str] = []
        lowered = content.lower()
        for rule in self._filter_rules.values():
            if not rule.enabled or not rule.pattern:
                continue
            if rule.pattern.lower() in lowered:
                filtered = True
                matched_rule_ids.append(rule.rule_id)
                if rule.action == "block":
                    blocked = True
                elif rule.action == "filter" and rule.replacement:
                    # Replace case-insensitively while preserving the rest.
                    final_content = final_content.replace(
                        rule.pattern, rule.replacement
                    )
                    final_content = final_content.replace(
                        rule.pattern.lower(), rule.replacement
                    )
                    final_content = final_content.replace(
                        rule.pattern.upper(), rule.replacement
                    )
        return final_content, filtered, matched_rule_ids, blocked

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Seed the system with default channels, users, messages, and a filter rule."""
        # Two seed channels: a global text channel and a team text channel.
        global_channel = ChatChannel(
            channel_id="ch_global",
            name="Global",
            channel_type=ChannelType.GLOBAL,
            owner_id="system",
            description="Server-wide global chat channel.",
            member_ids=["user_1", "user_2"],
            voice=False,
            max_members=_MAX_MEMBERS_PER_CHANNEL,
            slow_mode_seconds=0.0,
            metadata={"seed": True},
        )
        team_channel = ChatChannel(
            channel_id="ch_team_alpha",
            name="Team Alpha",
            channel_type=ChannelType.TEAM,
            owner_id="user_1",
            description="Private team channel for Alpha squad.",
            member_ids=["user_1", "user_2"],
            voice=False,
            max_members=8,
            slow_mode_seconds=1.0,
            metadata={"seed": True, "team": "alpha"},
        )
        self._channels[global_channel.channel_id] = global_channel
        self._channels[team_channel.channel_id] = team_channel
        self._stats.channel_counter = 2

        # Two seed users.
        user_1 = ChatUser(
            user_id="user_1",
            display_name="Alice",
            status=UserStatus.ONLINE,
            status_message="Exploring the realm",
            channel_ids=["ch_global", "ch_team_alpha"],
            muted_channels=[],
            role="moderator",
            metadata={"seed": True},
        )
        user_2 = ChatUser(
            user_id="user_2",
            display_name="Bob",
            status=UserStatus.ONLINE,
            status_message="",
            channel_ids=["ch_global", "ch_team_alpha"],
            muted_channels=[],
            role="player",
            metadata={"seed": True},
        )
        self._users[user_1.user_id] = user_1
        self._users[user_2.user_id] = user_2
        self._stats.user_counter = 2

        # Three seed messages across the two channels.
        msg_1 = ChatMessage(
            message_id="msg_seed_1",
            channel_id="ch_global",
            sender_id="user_1",
            content="Welcome to SparkLabs everyone!",
            status=MessageStatus.DELIVERED,
            filtered=False,
            mentions=[],
            created_at=_now(),
            delivered_at=_now(),
            metadata={"seed": True},
        )
        msg_2 = ChatMessage(
            message_id="msg_seed_2",
            channel_id="ch_global",
            sender_id="user_2",
            content="Hi Alice! Anyone want to group up?",
            status=MessageStatus.READ,
            filtered=False,
            mentions=["user_1"],
            created_at=_now(),
            delivered_at=_now(),
            read_at=_now(),
            metadata={"seed": True},
        )
        msg_3 = ChatMessage(
            message_id="msg_seed_3",
            channel_id="ch_team_alpha",
            sender_id="user_1",
            content="Team Alpha, regroup at the capital.",
            status=MessageStatus.SENT,
            filtered=False,
            mentions=[],
            created_at=_now(),
            metadata={"seed": True},
        )
        self._messages[msg_1.message_id] = msg_1
        self._messages[msg_2.message_id] = msg_2
        self._messages[msg_3.message_id] = msg_3
        self._stats.message_counter = 3
        self._stats.messages_sent = 3

        # One seed filter rule blocking profanity.
        profanity_rule = ChatFilterRule(
            rule_id="rule_profanity",
            name="Profanity Filter",
            category=FilterCategory.PROFANITY,
            pattern="badword",
            action="filter",
            replacement="****",
            enabled=True,
            severity=2,
            metadata={"seed": True},
        )
        self._filter_rules[profanity_rule.rule_id] = profanity_rule
        self._stats.filter_counter = 1

        # Refresh aggregate counts.
        self._stats.total_channels = len(self._channels)
        self._stats.total_messages = len(self._messages)
        self._stats.total_users = len(self._users)
        self._stats.total_filter_rules = len(self._filter_rules)
        self._stats.active_channels = sum(
            1 for c in self._channels.values() if c.member_ids
        )

    # ------------------------------------------------------------------
    # Channel Management
    # ------------------------------------------------------------------

    def create_channel(
        self,
        name: str,
        channel_type: ChannelType,
        owner_id: str = "",
        description: str = "",
        voice: bool = False,
        max_members: int = _MAX_MEMBERS_PER_CHANNEL,
        slow_mode_seconds: float = 0.0,
        channel_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatChannel:
        """Create a new chat channel.

        Args:
            name: Display name of the channel.
            channel_type: The ChannelType classification.
            owner_id: The user id who owns the channel.
            description: Human-readable description.
            voice: Whether this is a voice channel.
            max_members: Maximum number of members allowed.
            slow_mode_seconds: Minimum seconds between messages per user.
            channel_id: Optional explicit channel id.
            metadata: Optional free-form metadata bag.

        Returns:
            The newly created ChatChannel.
        """
        with self._lock:
            cid = channel_id or _new_id("ch")
            if cid in self._channels:
                raise ValueError(f"Channel already exists: {cid}")
            # Voice channels are implicitly typed as VOICE when voice is set.
            effective_type = (
                ChannelType.VOICE if voice and channel_type != ChannelType.VOICE
                else channel_type
            )
            channel = ChatChannel(
                channel_id=cid,
                name=name,
                channel_type=effective_type,
                owner_id=owner_id,
                description=description,
                member_ids=[],
                voice=voice or effective_type == ChannelType.VOICE,
                max_members=max_members,
                slow_mode_seconds=slow_mode_seconds,
                metadata=dict(metadata) if metadata else {},
            )
            self._channels[cid] = channel
            self._stats.channel_counter += 1
            self._stats.total_channels = len(self._channels)
            self._emit(
                ChatEventKind.CHANNEL_CREATED,
                {"channel_id": cid, "name": name, "channel_type": effective_type.value},
            )
            return channel

    def get_channel(self, channel_id: str) -> Optional[ChatChannel]:
        """Get a channel by id."""
        with self._lock:
            return self._channels.get(channel_id)

    def list_channels(
        self,
        channel_type: Optional[ChannelType] = None,
        member_id: Optional[str] = None,
        voice: Optional[bool] = None,
    ) -> List[ChatChannel]:
        """List channels with optional filters.

        Args:
            channel_type: Filter by ChannelType.
            member_id: Filter to channels containing this member.
            voice: Filter by voice flag.

        Returns:
            A list of matching ChatChannel instances.
        """
        with self._lock:
            result: List[ChatChannel] = []
            for channel in self._channels.values():
                if channel_type and channel.channel_type != channel_type:
                    continue
                if member_id and member_id not in channel.member_ids:
                    continue
                if voice is not None and channel.voice != voice:
                    continue
                result.append(channel)
            return result

    def delete_channel(self, channel_id: str) -> bool:
        """Delete a channel and remove it from its members' rosters.

        Returns:
            True if the channel was deleted, False if it did not exist.
        """
        with self._lock:
            channel = self._channels.get(channel_id)
            if channel is None:
                return False
            # Remove the channel from each member's channel list.
            for user_id in channel.member_ids:
                user = self._users.get(user_id)
                if user and channel_id in user.channel_ids:
                    user.channel_ids.remove(channel_id)
                    user.updated_at = _now()
            # Remove voice participants in this channel.
            to_remove = [
                pid for pid, vp in self._voice_participants.items()
                if vp.channel_id == channel_id
            ]
            for pid in to_remove:
                del self._voice_participants[pid]
            del self._channels[channel_id]
            self._stats.total_channels = len(self._channels)
            self._stats.total_voice_participants = len(self._voice_participants)
            self._stats.active_channels = sum(
                1 for c in self._channels.values() if c.member_ids
            )
            self._emit(
                ChatEventKind.CHANNEL_DELETED,
                {"channel_id": channel_id},
            )
            return True

    # ------------------------------------------------------------------
    # Channel Membership
    # ------------------------------------------------------------------

    def join_channel(self, channel_id: str, user_id: str) -> bool:
        """Add a user to a channel's member roster.

        For voice channels, a VoiceParticipant is also created.

        Returns:
            True if the user joined, False if already a member.
        """
        with self._lock:
            channel = self._channels.get(channel_id)
            if channel is None:
                raise ValueError(f"Channel does not exist: {channel_id}")
            user = self._users.get(user_id)
            if user is None:
                raise ValueError(f"User does not exist: {user_id}")
            if user_id in channel.member_ids:
                return False
            if len(channel.member_ids) >= channel.max_members:
                raise ValueError(f"Channel is full: {channel_id}")
            channel.member_ids.append(user_id)
            channel.updated_at = _now()
            if channel_id not in user.channel_ids:
                user.channel_ids.append(channel_id)
                user.updated_at = _now()
            self._stats.active_channels = sum(
                1 for c in self._channels.values() if c.member_ids
            )
            self._emit(
                ChatEventKind.USER_JOINED,
                {"channel_id": channel_id, "user_id": user_id},
            )
            # Track voice participation for voice channels.
            if channel.voice:
                participant = VoiceParticipant(
                    participant_id=_new_id("vp"),
                    user_id=user_id,
                    channel_id=channel_id,
                    joined_at=_now(),
                )
                self._voice_participants[participant.participant_id] = participant
                self._stats.total_voice_participants = len(self._voice_participants)
                if user.status != UserStatus.VOICE_CHAT:
                    user.status = UserStatus.VOICE_CHAT
                    user.updated_at = _now()
                self._emit(
                    ChatEventKind.VOICE_PARTICIPANT_JOINED,
                    {
                        "participant_id": participant.participant_id,
                        "channel_id": channel_id,
                        "user_id": user_id,
                    },
                )
            return True

    def leave_channel(self, channel_id: str, user_id: str) -> bool:
        """Remove a user from a channel's member roster.

        Returns:
            True if the user left, False if they were not a member.
        """
        with self._lock:
            channel = self._channels.get(channel_id)
            if channel is None:
                raise ValueError(f"Channel does not exist: {channel_id}")
            if user_id not in channel.member_ids:
                return False
            channel.member_ids.remove(user_id)
            channel.updated_at = _now()
            user = self._users.get(user_id)
            if user and channel_id in user.channel_ids:
                user.channel_ids.remove(channel_id)
                user.updated_at = _now()
            # Remove any voice participation for this user in this channel.
            to_remove = [
                pid for pid, vp in self._voice_participants.items()
                if vp.channel_id == channel_id and vp.user_id == user_id
            ]
            for pid in to_remove:
                del self._voice_participants[pid]
                self._emit(
                    ChatEventKind.VOICE_PARTICIPANT_LEFT,
                    {"participant_id": pid, "channel_id": channel_id, "user_id": user_id},
                )
            self._stats.total_voice_participants = len(self._voice_participants)
            self._stats.active_channels = sum(
                1 for c in self._channels.values() if c.member_ids
            )
            self._emit(
                ChatEventKind.USER_LEFT,
                {"channel_id": channel_id, "user_id": user_id},
            )
            return True

    # ------------------------------------------------------------------
    # Message Management
    # ------------------------------------------------------------------

    def send_message(
        self,
        channel_id: str,
        sender_id: str,
        content: str,
        mentions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Send a message to a channel.

        Applies enabled filter rules before storing. If a rule blocks
        the message, the status is set to FILTERED and the original
        content is preserved in ``original_content``.

        Args:
            channel_id: The target channel id.
            sender_id: The sender's user id.
            content: The message text.
            mentions: Optional list of mentioned user ids.
            metadata: Optional free-form metadata bag.

        Returns:
            The newly created ChatMessage.
        """
        with self._lock:
            channel = self._channels.get(channel_id)
            if channel is None:
                raise ValueError(f"Channel does not exist: {channel_id}")
            user = self._users.get(sender_id)
            if user is None:
                raise ValueError(f"User does not exist: {sender_id}")
            # Enforce per-channel mute state.
            if channel_id in user.muted_channels:
                raise ValueError(f"User is muted in channel: {channel_id}")
            # Apply content filters.
            final_content, filtered, matched_rule_ids, blocked = self._apply_filters(
                content
            )
            now = _now()
            if blocked:
                status = MessageStatus.FILTERED
                final_content = ""
                original_content = content
            elif filtered:
                status = MessageStatus.FILTERED
                original_content = content
            else:
                status = MessageStatus.SENT
                original_content = ""
            message = ChatMessage(
                message_id=_new_id("msg"),
                channel_id=channel_id,
                sender_id=sender_id,
                content=final_content,
                status=status,
                filtered=filtered or blocked,
                original_content=original_content,
                matched_rule_ids=matched_rule_ids,
                mentions=list(mentions) if mentions else [],
                edited=False,
                created_at=now,
                delivered_at=now if status != MessageStatus.FILTERED else "",
                metadata=dict(metadata) if metadata else {},
            )
            self._messages[message.message_id] = message
            _evict_fifo_dict(self._messages, _MAX_MESSAGES)
            self._stats.message_counter += 1
            self._stats.messages_sent += 1
            self._stats.total_messages = len(self._messages)
            if filtered or blocked:
                self._stats.messages_filtered += 1
                self._emit(
                    ChatEventKind.MESSAGE_FILTERED,
                    {
                        "message_id": message.message_id,
                        "channel_id": channel_id,
                        "sender_id": sender_id,
                        "matched_rule_ids": matched_rule_ids,
                        "blocked": blocked,
                    },
                )
            self._emit(
                ChatEventKind.MESSAGE_SENT,
                {
                    "message_id": message.message_id,
                    "channel_id": channel_id,
                    "sender_id": sender_id,
                    "status": status.value,
                },
            )
            return message

    def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """Get a message by id."""
        with self._lock:
            return self._messages.get(message_id)

    def list_messages(
        self,
        channel_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        status: Optional[MessageStatus] = None,
        limit: int = 100,
    ) -> List[ChatMessage]:
        """List messages with optional filters.

        Args:
            channel_id: Filter by channel.
            sender_id: Filter by sender.
            status: Filter by MessageStatus.
            limit: Maximum number of messages to return.

        Returns:
            A list of matching ChatMessage instances.
        """
        with self._lock:
            result: List[ChatMessage] = []
            for message in self._messages.values():
                if channel_id and message.channel_id != channel_id:
                    continue
                if sender_id and message.sender_id != sender_id:
                    continue
                if status and message.status != status:
                    continue
                result.append(message)
            # Return the most recent ``limit`` messages in insertion order.
            if limit > 0:
                result = result[-limit:]
            return result

    def delete_message(self, message_id: str) -> bool:
        """Soft-delete a message by marking its status as DELETED.

        Returns:
            True if the message was deleted, False if it did not exist.
        """
        with self._lock:
            message = self._messages.get(message_id)
            if message is None:
                return False
            message.status = MessageStatus.DELETED
            message.content = ""
            message.original_content = ""
            message.edited_at = _now()
            self._emit(
                ChatEventKind.MESSAGE_DELETED,
                {"message_id": message_id, "channel_id": message.channel_id},
            )
            return True

    # ------------------------------------------------------------------
    # User Management
    # ------------------------------------------------------------------

    def register_user(
        self,
        display_name: str,
        status: UserStatus = UserStatus.ONLINE,
        status_message: str = "",
        role: str = "player",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatUser:
        """Register a new chat user.

        Args:
            display_name: Display name shown in chat.
            status: The initial UserStatus.
            status_message: Optional custom status message.
            role: The user role (e.g. "player", "moderator", "admin").
            user_id: Optional explicit user id.
            metadata: Optional free-form metadata bag.

        Returns:
            The newly created ChatUser.
        """
        with self._lock:
            uid = user_id or _new_id("user")
            if uid in self._users:
                raise ValueError(f"User already exists: {uid}")
            user = ChatUser(
                user_id=uid,
                display_name=display_name,
                status=status,
                status_message=status_message,
                channel_ids=[],
                muted_channels=[],
                role=role,
                metadata=dict(metadata) if metadata else {},
            )
            self._users[uid] = user
            self._stats.user_counter += 1
            self._stats.total_users = len(self._users)
            self._emit(
                ChatEventKind.USER_REGISTERED,
                {"user_id": uid, "display_name": display_name, "role": role},
            )
            return user

    def get_user(self, user_id: str) -> Optional[ChatUser]:
        """Get a user by id."""
        with self._lock:
            return self._users.get(user_id)

    def update_user_status(
        self,
        user_id: str,
        status: UserStatus,
        status_message: Optional[str] = None,
    ) -> Optional[ChatUser]:
        """Update a user's presence status.

        Args:
            user_id: The user id to update.
            status: The new UserStatus.
            status_message: Optional new status message.

        Returns:
            The updated ChatUser, or None if the user does not exist.
        """
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return None
            user.status = status
            if status_message is not None:
                user.status_message = status_message
            user.last_seen = _now()
            user.updated_at = _now()
            self._emit(
                ChatEventKind.USER_STATUS_UPDATED,
                {"user_id": user_id, "status": status.value},
            )
            return user

    def list_users(
        self,
        status: Optional[UserStatus] = None,
        role: Optional[str] = None,
    ) -> List[ChatUser]:
        """List users with optional filters.

        Args:
            status: Filter by UserStatus.
            role: Filter by role.

        Returns:
            A list of matching ChatUser instances.
        """
        with self._lock:
            result: List[ChatUser] = []
            for user in self._users.values():
                if status and user.status != status:
                    continue
                if role and user.role != role:
                    continue
                result.append(user)
            return result

    # ------------------------------------------------------------------
    # Filter Rule Management
    # ------------------------------------------------------------------

    def create_filter_rule(
        self,
        name: str,
        category: FilterCategory,
        pattern: str,
        action: str = "flag",
        replacement: str = "",
        enabled: bool = True,
        severity: int = 1,
        rule_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatFilterRule:
        """Create a new content filter rule.

        Args:
            name: Display name of the rule.
            category: The FilterCategory classification.
            pattern: Case-insensitive substring pattern to match.
            action: Action to take ("flag", "filter", or "block").
            replacement: Optional replacement text for filtered content.
            enabled: Whether the rule is active.
            severity: Severity level from 0 (info) to 3 (critical).
            rule_id: Optional explicit rule id.
            metadata: Optional free-form metadata bag.

        Returns:
            The newly created ChatFilterRule.
        """
        with self._lock:
            rid = rule_id or _new_id("rule")
            if rid in self._filter_rules:
                raise ValueError(f"Filter rule already exists: {rid}")
            rule = ChatFilterRule(
                rule_id=rid,
                name=name,
                category=category,
                pattern=pattern,
                action=action,
                replacement=replacement,
                enabled=enabled,
                severity=severity,
                metadata=dict(metadata) if metadata else {},
            )
            self._filter_rules[rid] = rule
            _evict_fifo_dict(self._filter_rules, _MAX_FILTER_RULES)
            self._stats.filter_counter += 1
            self._stats.total_filter_rules = len(self._filter_rules)
            self._emit(
                ChatEventKind.FILTER_RULE_CREATED,
                {"rule_id": rid, "name": name, "category": category.value},
            )
            return rule

    def get_filter_rule(self, rule_id: str) -> Optional[ChatFilterRule]:
        """Get a filter rule by id."""
        with self._lock:
            return self._filter_rules.get(rule_id)

    def list_filter_rules(
        self,
        category: Optional[FilterCategory] = None,
        enabled: Optional[bool] = None,
    ) -> List[ChatFilterRule]:
        """List filter rules with optional filters.

        Args:
            category: Filter by FilterCategory.
            enabled: Filter by enabled state.

        Returns:
            A list of matching ChatFilterRule instances.
        """
        with self._lock:
            result: List[ChatFilterRule] = []
            for rule in self._filter_rules.values():
                if category and rule.category != category:
                    continue
                if enabled is not None and rule.enabled != enabled:
                    continue
                result.append(rule)
            return result

    def delete_filter_rule(self, rule_id: str) -> bool:
        """Delete a filter rule.

        Returns:
            True if the rule was deleted, False if it did not exist.
        """
        with self._lock:
            if rule_id not in self._filter_rules:
                return False
            del self._filter_rules[rule_id]
            self._stats.total_filter_rules = len(self._filter_rules)
            self._emit(
                ChatEventKind.FILTER_RULE_DELETED,
                {"rule_id": rule_id},
            )
            return True

    # ------------------------------------------------------------------
    # Moderation
    # ------------------------------------------------------------------

    def moderate_user(
        self,
        moderator_id: str,
        target_user_id: str,
        action_type: ModerationActionType,
        reason: str = "",
        channel_id: str = "",
        duration_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModerationAction:
        """Apply a moderation action to a user.

        Mute and shadow-mute add the channel to the user's muted list
        (or all their channels if ``channel_id`` is empty). Ban sets the
        user's status to offline. Kick removes the user from the channel.

        Args:
            moderator_id: The user id of the moderator.
            target_user_id: The user id of the moderated user.
            action_type: The ModerationActionType.
            reason: Human-readable reason for the action.
            channel_id: The channel the action applies to (empty for global).
            duration_seconds: Duration in seconds (0 means permanent).
            metadata: Optional free-form metadata bag.

        Returns:
            The newly created ModerationAction.
        """
        with self._lock:
            if target_user_id not in self._users:
                raise ValueError(f"Target user does not exist: {target_user_id}")
            target = self._users[target_user_id]
            expires_at = ""
            if duration_seconds > 0:
                expires_dt = datetime.utcnow() + timedelta(seconds=duration_seconds)
                expires_at = expires_dt.isoformat() + "Z"
            action = ModerationAction(
                action_id=_new_id("mod"),
                moderator_id=moderator_id,
                target_user_id=target_user_id,
                action_type=action_type,
                channel_id=channel_id,
                reason=reason,
                duration_seconds=duration_seconds,
                expires_at=expires_at,
                active=True,
                metadata=dict(metadata) if metadata else {},
            )
            self._moderation_actions[action.action_id] = action
            _evict_fifo_dict(self._moderation_actions, _MAX_MODERATION_ACTIONS)
            self._stats.moderation_counter += 1
            self._stats.total_moderation_actions = len(self._moderation_actions)

            # Apply the action's effects.
            if action_type in (
                ModerationActionType.MUTE,
                ModerationActionType.SHADOW_MUTE,
            ):
                if channel_id:
                    if channel_id not in target.muted_channels:
                        target.muted_channels.append(channel_id)
                else:
                    for cid in list(target.channel_ids):
                        if cid not in target.muted_channels:
                            target.muted_channels.append(cid)
                self._stats.active_mutes += 1
                target.updated_at = _now()
            elif action_type == ModerationActionType.BAN:
                target.status = UserStatus.OFFLINE
                target.updated_at = _now()
                self._stats.active_mutes += 1
            elif action_type == ModerationActionType.KICK:
                if channel_id and channel_id in target.channel_ids:
                    # Reuse leave_channel logic by inlining the removal.
                    channel = self._channels.get(channel_id)
                    if channel and target_user_id in channel.member_ids:
                        channel.member_ids.remove(target_user_id)
                        channel.updated_at = _now()
                    target.channel_ids.remove(channel_id)
                    target.updated_at = _now()

            self._emit(
                ChatEventKind.MODERATION_ACTION,
                {
                    "action_id": action.action_id,
                    "moderator_id": moderator_id,
                    "target_user_id": target_user_id,
                    "action_type": action_type.value,
                    "channel_id": channel_id,
                    "reason": reason,
                    "duration_seconds": duration_seconds,
                },
            )
            return action

    def list_moderation_actions(
        self,
        target_user_id: Optional[str] = None,
        action_type: Optional[ModerationActionType] = None,
        active: Optional[bool] = None,
        limit: int = 100,
    ) -> List[ModerationAction]:
        """List moderation actions with optional filters.

        Args:
            target_user_id: Filter by target user.
            action_type: Filter by ModerationActionType.
            active: Filter by active state.
            limit: Maximum number of actions to return.

        Returns:
            A list of matching ModerationAction instances.
        """
        with self._lock:
            result: List[ModerationAction] = []
            for action in self._moderation_actions.values():
                if target_user_id and action.target_user_id != target_user_id:
                    continue
                if action_type and action.action_type != action_type:
                    continue
                if active is not None and action.active != active:
                    continue
                result.append(action)
            if limit > 0:
                result = result[-limit:]
            return result

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events_log(self, limit: int = 100) -> List[ChatEvent]:
        """List recent audit events."""
        with self._lock:
            if limit <= 0:
                return list(self._events)
            return list(self._events[-limit:])

    def get_stats(self) -> ChatStats:
        """Return aggregate statistics."""
        with self._lock:
            self._stats.total_channels = len(self._channels)
            self._stats.total_messages = len(self._messages)
            self._stats.total_users = len(self._users)
            self._stats.total_filter_rules = len(self._filter_rules)
            self._stats.total_moderation_actions = len(self._moderation_actions)
            self._stats.total_voice_participants = len(self._voice_participants)
            self._stats.active_channels = sum(
                1 for c in self._channels.values() if c.member_ids
            )
            self._stats.active_mutes = sum(
                1
                for a in self._moderation_actions.values()
                if a.active
                and a.action_type
                in (
                    ModerationActionType.MUTE,
                    ModerationActionType.SHADOW_MUTE,
                    ModerationActionType.BAN,
                )
            )
            self._stats.total_events = len(self._events)
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Return a status summary."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_channels": len(self._channels),
                "total_messages": len(self._messages),
                "total_users": len(self._users),
                "total_filter_rules": len(self._filter_rules),
                "total_moderation_actions": len(self._moderation_actions),
                "total_voice_participants": len(self._voice_participants),
                "active_channels": sum(
                    1 for c in self._channels.values() if c.member_ids
                ),
                "messages_sent": self._stats.messages_sent,
                "messages_filtered": self._stats.messages_filtered,
                "active_mutes": sum(
                    1
                    for a in self._moderation_actions.values()
                    if a.active
                    and a.action_type
                    in (
                        ModerationActionType.MUTE,
                        ModerationActionType.SHADOW_MUTE,
                        ModerationActionType.BAN,
                    )
                ),
                "total_events": len(self._events),
                "capacities": {
                    "max_channels": _MAX_CHANNELS,
                    "max_messages": _MAX_MESSAGES,
                    "max_users": _MAX_USERS,
                    "max_filter_rules": _MAX_FILTER_RULES,
                    "max_moderation_actions": _MAX_MODERATION_ACTIONS,
                    "max_voice_participants": _MAX_VOICE_PARTICIPANTS,
                    "max_members_per_channel": _MAX_MEMBERS_PER_CHANNEL,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> ChatSnapshot:
        """Capture a snapshot of the entire system state."""
        with self._lock:
            return ChatSnapshot(
                channels=[c.to_dict() for c in self._channels.values()],
                messages=[m.to_dict() for m in self._messages.values()],
                users=[u.to_dict() for u in self._users.values()],
                filter_rules=[r.to_dict() for r in self._filter_rules.values()],
                moderation_actions=[a.to_dict() for a in self._moderation_actions.values()],
                voice_participants=[v.to_dict() for v in self._voice_participants.values()],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        """Reset the system to an empty state (clears all data)."""
        with self._lock:
            self._channels.clear()
            self._messages.clear()
            self._users.clear()
            self._filter_rules.clear()
            self._moderation_actions.clear()
            self._voice_participants.clear()
            self._events.clear()
            self._stats = ChatStats()
            self._emit(ChatEventKind.SYSTEM_RESET, {})


def get_chat_system() -> ChatSystem:
    """Return the singleton ChatSystem instance."""
    return ChatSystem()
