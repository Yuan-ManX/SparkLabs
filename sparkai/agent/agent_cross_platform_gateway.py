"""
SparkAI Agent - Cross-Platform Communication Gateway

Unified multi-platform messaging gateway that enables the SparkAI Agent
to communicate across Telegram, Discord, Slack, Web, and CLI interfaces
through a single gateway process. Supports conversation continuity,
cross-platform message routing, and platform-specific delivery.

Provides a unified abstraction layer over multiple messaging platforms
with consistent message formatting, command handling, and session
management across all connected platforms.
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PlatformType(str, Enum):
    WEB = "web"
    CLI = "cli"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    API = "api"
    WEBSOCKET = "websocket"
    MOBILE = "mobile"


class PlatformState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    PAUSED = "paused"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageFormat(str, Enum):
    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"
    RICH = "rich"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PlatformConnection:
    """Represents a connection to a messaging platform."""
    connection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    platform_type: PlatformType = PlatformType.WEB
    state: PlatformState = PlatformState.DISCONNECTED
    display_name: str = ""
    user_id: str = ""
    channel_id: str = ""
    connected_at: float = 0.0
    last_heartbeat: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    error_count: int = 0
    last_error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_primary: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "platform_type": self.platform_type.value,
            "state": self.state.value,
            "display_name": self.display_name,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "is_primary": self.is_primary,
        }


@dataclass
class GatewayMessage:
    """A message routed through the gateway."""
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_platform: PlatformType = PlatformType.WEB
    target_platform: Optional[PlatformType] = None
    sender_id: str = ""
    sender_name: str = ""
    content: str = ""
    format: MessageFormat = MessageFormat.PLAIN
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=_time_module.time)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_command: bool = False
    command_name: str = ""
    is_read: bool = False
    is_delivered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "source_platform": self.source_platform.value,
            "target_platform": self.target_platform.value if self.target_platform else None,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "format": self.format.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "thread_id": self.thread_id,
            "attachments": self.attachments,
            "is_command": self.is_command,
            "command_name": self.command_name,
            "is_read": self.is_read,
            "is_delivered": self.is_delivered,
        }


@dataclass
class Conversation:
    """A cross-platform conversation."""
    conversation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    participants: List[str] = field(default_factory=list)
    platforms: List[PlatformType] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    last_activity: float = field(default_factory=_time_module.time)
    is_active: bool = True
    tags: List[str] = field(default_factory=list)
    context_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "participants": self.participants,
            "platforms": [p.value for p in self.platforms],
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "is_active": self.is_active,
            "tags": self.tags,
            "context_summary": self.context_summary,
        }


# ---------------------------------------------------------------------------
# Cross-Platform Gateway
# ---------------------------------------------------------------------------

class AgentCrossPlatformGateway:
    """
    Unified cross-platform messaging gateway.

    Routes messages across multiple platforms (Telegram, Discord,
    Slack, Web, CLI) with conversation continuity, message history,
    and platform-specific delivery handling.
    """

    _instance: Optional["AgentCrossPlatformGateway"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentCrossPlatformGateway":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentCrossPlatformGateway":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._connections: Dict[str, PlatformConnection] = {}
        self._messages: Dict[str, GatewayMessage] = {}
        self._conversations: Dict[str, Conversation] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._command_handlers: Dict[str, Callable] = {}
        self._pending_messages: Dict[str, List[str]] = {}
        self._total_messages_processed: int = 0
        self._total_commands_processed: int = 0
        self._active_conversations: int = 0

    # ------------------------------------------------------------------
    # Platform Connection Management
    # ------------------------------------------------------------------

    def connect_platform(
        self, platform_type: PlatformType,
        user_id: str = "", display_name: str = "",
        channel_id: str = "", is_primary: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlatformConnection:
        """Register a new platform connection."""
        with self._lock:
            connection = PlatformConnection(
                platform_type=platform_type,
                state=PlatformState.CONNECTED,
                display_name=display_name or f"{platform_type.value}_user",
                user_id=user_id,
                channel_id=channel_id,
                connected_at=_time_module.time(),
                last_heartbeat=_time_module.time(),
                is_primary=is_primary,
                metadata=metadata or {},
            )
            if is_primary:
                # Ensure only one primary connection
                for conn in self._connections.values():
                    conn.is_primary = False
            self._connections[connection.connection_id] = connection
            return connection

    def disconnect_platform(self, connection_id: str) -> bool:
        """Disconnect a platform."""
        with self._lock:
            conn = self._connections.get(connection_id)
            if conn:
                conn.state = PlatformState.DISCONNECTED
                return True
            return False

    def heartbeat(self, connection_id: str) -> bool:
        """Update heartbeat timestamp for a connection."""
        with self._lock:
            conn = self._connections.get(connection_id)
            if conn:
                conn.last_heartbeat = _time_module.time()
                return True
            return False

    # ------------------------------------------------------------------
    # Message Routing
    # ------------------------------------------------------------------

    def send_message(
        self, content: str, source_connection_id: str,
        target_platform: Optional[PlatformType] = None,
        target_connection_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        message_format: MessageFormat = MessageFormat.PLAIN,
        reply_to: Optional[str] = None,
        thread_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> GatewayMessage:
        """Send a message through the gateway."""
        with self._lock:
            source_conn = self._connections.get(source_connection_id)
            if not source_conn:
                raise ValueError(f"Source connection {source_connection_id} not found")

            message = GatewayMessage(
                source_platform=source_conn.platform_type,
                target_platform=target_platform,
                sender_id=source_conn.user_id,
                sender_name=source_conn.display_name,
                content=content,
                format=message_format,
                priority=priority,
                reply_to=reply_to,
                thread_id=thread_id,
                attachments=attachments or [],
            )

            self._messages[message.message_id] = message
            source_conn.messages_sent += 1

            # Route to specific target
            if target_connection_id:
                target_conn = self._connections.get(target_connection_id)
                if target_conn:
                    message.is_delivered = True
                    target_conn.messages_received += 1

            # Broadcast to all if no specific target
            elif target_platform:
                for conn in self._connections.values():
                    if conn.connection_id != source_connection_id:
                        if conn.platform_type == target_platform:
                            conn.messages_received += 1
                message.is_delivered = True

            self._total_messages_processed += 1
            return message

    def receive_message(
        self, connection_id: str, content: str,
        sender_name: str = "",
        message_format: MessageFormat = MessageFormat.PLAIN,
        reply_to: Optional[str] = None,
        is_command: bool = False,
    ) -> GatewayMessage:
        """Receive a message from a platform."""
        with self._lock:
            conn = self._connections.get(connection_id)
            if not conn:
                raise ValueError(f"Connection {connection_id} not found")

            message = GatewayMessage(
                source_platform=conn.platform_type,
                sender_id=conn.user_id,
                sender_name=sender_name or conn.display_name,
                content=content,
                format=message_format,
                reply_to=reply_to,
                is_command=is_command,
                command_name=content.split()[0].lstrip("/") if is_command else "",
            )

            self._messages[message.message_id] = message
            conn.messages_received += 1
            self._total_messages_processed += 1

            if is_command:
                self._total_commands_processed += 1

            return message

    # ------------------------------------------------------------------
    # Command Handling
    # ------------------------------------------------------------------

    def register_command(
        self, command_name: str, handler: Callable,
        description: str = "", platform_filter: Optional[List[PlatformType]] = None,
    ) -> str:
        """Register a command handler."""
        with self._lock:
            cmd_id = uuid.uuid4().hex
            self._command_handlers[command_name] = {
                "handler": handler,
                "description": description,
                "platform_filter": platform_filter or [],
                "registered_at": _time_module.time(),
                "invocation_count": 0,
            }
            return cmd_id

    def execute_command(
        self, command_name: str, args: List[str],
        connection_id: str,
    ) -> Dict[str, Any]:
        """Execute a registered command."""
        with self._lock:
            handler_info = self._command_handlers.get(command_name)
            if not handler_info:
                return {"error": f"Unknown command: {command_name}"}

            conn = self._connections.get(connection_id)
            if not conn:
                return {"error": "Connection not found"}

            platform = conn.platform_type
            if handler_info["platform_filter"] and platform not in handler_info["platform_filter"]:
                return {"error": f"Command not available on {platform.value}"}

            try:
                result = handler_info["handler"](args, conn)
                handler_info["invocation_count"] += 1
                return {"success": True, "result": result}
            except Exception as e:
                return {"error": str(e)}

    # ------------------------------------------------------------------
    # Conversation Management
    # ------------------------------------------------------------------

    def create_conversation(
        self, title: str = "",
        participants: Optional[List[str]] = None,
        platforms: Optional[List[PlatformType]] = None,
        tags: Optional[List[str]] = None,
    ) -> Conversation:
        """Create a new cross-platform conversation."""
        with self._lock:
            conversation = Conversation(
                title=title,
                participants=participants or [],
                platforms=platforms or [],
                tags=tags or [],
            )
            self._conversations[conversation.conversation_id] = conversation
            self._active_conversations += 1
            return conversation

    def add_message_to_conversation(
        self, conversation_id: str, message_id: str,
    ) -> bool:
        """Add a message to a conversation."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return False
            conv.messages.append(message_id)
            conv.last_activity = _time_module.time()
            return True

    def get_conversation_history(
        self, conversation_id: str, limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get the message history for a conversation."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return []
            messages = []
            for msg_id in conv.messages[-limit:]:
                msg = self._messages.get(msg_id)
                if msg:
                    messages.append(msg.to_dict())
            return messages

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_gateway_stats(self) -> Dict[str, Any]:
        """Get overall gateway statistics."""
        with self._lock:
            platform_stats = {}
            for conn in self._connections.values():
                pt = conn.platform_type.value
                if pt not in platform_stats:
                    platform_stats[pt] = {
                        "connections": 0,
                        "connected": 0,
                        "messages_sent": 0,
                        "messages_received": 0,
                    }
                platform_stats[pt]["connections"] += 1
                if conn.state == PlatformState.CONNECTED:
                    platform_stats[pt]["connected"] += 1
                platform_stats[pt]["messages_sent"] += conn.messages_sent
                platform_stats[pt]["messages_received"] += conn.messages_received

            return {
                "total_connections": len(self._connections),
                "active_connections": sum(
                    1 for c in self._connections.values()
                    if c.state == PlatformState.CONNECTED
                ),
                "total_messages": self._total_messages_processed,
                "total_commands": self._total_commands_processed,
                "active_conversations": self._active_conversations,
                "registered_commands": len(self._command_handlers),
                "platform_stats": platform_stats,
                "connections": [
                    c.to_dict() for c in self._connections.values()
                ],
            }

    def get_active_connections(self) -> List[Dict[str, Any]]:
        """Get list of currently active connections."""
        with self._lock:
            return [
                c.to_dict() for c in self._connections.values()
                if c.state == PlatformState.CONNECTED
            ]

    def get_pending_messages(self) -> Dict[str, int]:
        """Get count of pending messages per platform."""
        with self._lock:
            return {
                pid: len(msgs) for pid, msgs in self._pending_messages.items()
            }

    def cleanup_stale_connections(self, max_idle_seconds: float = 300.0) -> int:
        """Disconnect stale connections. Returns count of disconnected."""
        with self._lock:
            now = _time_module.time()
            count = 0
            for conn in self._connections.values():
                if conn.state == PlatformState.CONNECTED:
                    if now - conn.last_heartbeat > max_idle_seconds:
                        conn.state = PlatformState.DISCONNECTED
                        count += 1
            return count


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_cross_platform_gateway() -> AgentCrossPlatformGateway:
    return AgentCrossPlatformGateway.get_instance()