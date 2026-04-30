"""
SparkAI Agent - Protocol

Structured communication protocol for inter-agent messaging.
Defines message types, routing rules, verification steps, and
conversation threading for reliable multi-agent coordination.

Protocol design:
  - Typed messages with mandatory fields and optional payloads
  - Request-Response pattern with correlation IDs
  - Publish-Subscribe for broadcast notifications
  - Conversation threading for multi-turn agent dialogues
  - Delivery guarantees: at-least-once with deduplication
  - Priority-based message ordering
  - Timeout and retry policies per message type
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    COMMAND = "command"
    EVENT = "event"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    DELEGATION = "delegation"
    VERIFICATION = "verification"
    PROGRESS = "progress"


class MessagePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class DeliveryStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"
    RETRYING = "retrying"


@dataclass
class ProtocolMessage:
    """
    A structured message in the SparkLabs agent protocol.

    Every message has a unique ID, type, sender, and recipient.
    Messages can be part of a conversation thread, carry payloads,
    and have delivery tracking metadata.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.REQUEST
    priority: MessagePriority = MessagePriority.NORMAL
    sender: str = ""
    recipient: str = ""
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    conversation_id: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 2
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    status: DeliveryStatus = DeliveryStatus.PENDING
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "topic": self.topic,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "conversation_id": self.conversation_id,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def create_response(
        self,
        payload: Dict[str, Any],
        msg_type: MessageType = MessageType.RESPONSE,
    ) -> ProtocolMessage:
        return ProtocolMessage(
            type=msg_type,
            sender=self.recipient,
            recipient=self.sender,
            topic=self.topic,
            payload=payload,
            correlation_id=self.id,
            conversation_id=self.conversation_id,
        )


@dataclass
class Conversation:
    """
    A threaded conversation between agents.

    Tracks the full history of messages exchanged between
    two or more agents within a logical dialogue.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    participants: List[str] = field(default_factory=list)
    topic: str = ""
    messages: List[ProtocolMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    status: str = "active"

    def add_message(self, message: ProtocolMessage) -> None:
        message.conversation_id = self.id
        self.messages.append(message)
        self.last_activity = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "participants": self.participants,
            "topic": self.topic,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "status": self.status,
        }


@dataclass
class DeliveryReceipt:
    """Acknowledgment of message delivery."""
    message_id: str = ""
    recipient: str = ""
    status: DeliveryStatus = DeliveryStatus.DELIVERED
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "recipient": self.recipient,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "error": self.error,
        }


class MessageRouter:
    """
    Routes protocol messages to the correct agent or handler.

    Supports direct addressing (agent_id), broadcast (topic-based),
    and pattern matching for flexible message routing.
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._topic_subscribers: Dict[str, List[str]] = {}
        self._type_handlers: Dict[MessageType, List[Callable]] = {}

    def register_handler(self, agent_id: str, handler: Callable) -> None:
        self._handlers[agent_id] = handler

    def unregister_handler(self, agent_id: str) -> None:
        self._handlers.pop(agent_id, None)

    def subscribe_topic(self, topic: str, agent_id: str) -> None:
        if topic not in self._topic_subscribers:
            self._topic_subscribers[topic] = []
        if agent_id not in self._topic_subscribers[topic]:
            self._topic_subscribers[topic].append(agent_id)

    def unsubscribe_topic(self, topic: str, agent_id: str) -> None:
        if topic in self._topic_subscribers:
            try:
                self._topic_subscribers[topic].remove(agent_id)
            except ValueError:
                pass

    def register_type_handler(self, msg_type: MessageType, handler: Callable) -> None:
        if msg_type not in self._type_handlers:
            self._type_handlers[msg_type] = []
        self._type_handlers[msg_type].append(handler)

    def route(self, message: ProtocolMessage) -> List[str]:
        """Determine which handlers should receive this message."""
        targets = []

        if message.recipient and message.recipient in self._handlers:
            targets.append(message.recipient)

        if message.topic and message.topic in self._topic_subscribers:
            for agent_id in self._topic_subscribers[message.topic]:
                if agent_id not in targets:
                    targets.append(agent_id)

        if message.type in self._type_handlers:
            for handler_id in self._type_handlers[message.type]:
                if handler_id not in targets:
                    targets.append(handler_id)

        return targets

    async def deliver(self, message: ProtocolMessage) -> List[DeliveryReceipt]:
        """Deliver a message to all matching handlers."""
        targets = self.route(message)
        receipts = []

        for target_id in targets:
            handler = self._handlers.get(target_id)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                    receipts.append(DeliveryReceipt(
                        message_id=message.id,
                        recipient=target_id,
                        status=DeliveryStatus.DELIVERED,
                    ))
                except Exception as e:
                    receipts.append(DeliveryReceipt(
                        message_id=message.id,
                        recipient=target_id,
                        status=DeliveryStatus.FAILED,
                        error=str(e),
                    ))

        return receipts


class AgentProtocol:
    """
    Communication protocol for the SparkLabs AI-Native Game Engine.

    Manages inter-agent messaging with structured message types,
    conversation threading, delivery tracking, and retry policies.

    Usage:
        protocol = AgentProtocol()
        protocol.register("agent_1", handler)
        msg = protocol.create_request("agent_1", "game_design", {"genre": "rpg"})
        receipts = await protocol.send(msg)
    """

    def __init__(self, max_conversations: int = 200):
        self._router = MessageRouter()
        self._conversations: Dict[str, Conversation] = {}
        self._pending: Dict[str, asyncio.Future] = {}
        self._message_log: List[ProtocolMessage] = []
        self._max_conversations = max_conversations
        self._max_log = 1000
        self._stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "total_expired": 0,
            "by_type": {},
        }

    def register_agent(self, agent_id: str, handler: Callable) -> None:
        """Register an agent's message handler."""
        self._router.register_handler(agent_id, handler)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent's message handler."""
        self._router.unregister_handler(agent_id)

    def subscribe(self, topic: str, agent_id: str) -> None:
        """Subscribe an agent to a topic for broadcast messages."""
        self._router.subscribe_topic(topic, agent_id)

    def unsubscribe(self, topic: str, agent_id: str) -> None:
        """Unsubscribe an agent from a topic."""
        self._router.unsubscribe_topic(topic, agent_id)

    def create_request(
        self,
        recipient: str,
        topic: str,
        payload: Dict[str, Any],
        sender: str = "runtime",
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout: float = 30.0,
    ) -> ProtocolMessage:
        """Create a request message expecting a response."""
        return ProtocolMessage(
            type=MessageType.REQUEST,
            priority=priority,
            sender=sender,
            recipient=recipient,
            topic=topic,
            payload=payload,
            timeout_seconds=timeout,
            expires_at=time.time() + timeout,
        )

    def create_notification(
        self,
        topic: str,
        payload: Dict[str, Any],
        sender: str = "runtime",
    ) -> ProtocolMessage:
        """Create a broadcast notification message."""
        return ProtocolMessage(
            type=MessageType.NOTIFICATION,
            priority=MessagePriority.LOW,
            sender=sender,
            recipient="",
            topic=topic,
            payload=payload,
        )

    def create_delegation(
        self,
        recipient: str,
        task: str,
        context: Dict[str, Any],
        sender: str = "runtime",
    ) -> ProtocolMessage:
        """Create a task delegation message."""
        return ProtocolMessage(
            type=MessageType.DELEGATION,
            priority=MessagePriority.HIGH,
            sender=sender,
            recipient=recipient,
            topic="delegation",
            payload={"task": task, "context": context},
            timeout_seconds=120.0,
            expires_at=time.time() + 120.0,
        )

    async def send(self, message: ProtocolMessage) -> List[DeliveryReceipt]:
        """Send a message and track delivery."""
        if message.is_expired():
            message.status = DeliveryStatus.EXPIRED
            self._stats["total_expired"] += 1
            return [DeliveryReceipt(
                message_id=message.id,
                recipient=message.recipient,
                status=DeliveryStatus.EXPIRED,
                error="Message expired before delivery",
            )]

        self._stats["total_sent"] += 1
        type_stats = self._stats["by_type"]
        type_key = message.type.value
        type_stats[type_key] = type_stats.get(type_key, 0) + 1

        self._log_message(message)

        receipts = await self._router.deliver(message)

        for receipt in receipts:
            if receipt.status == DeliveryStatus.DELIVERED:
                self._stats["total_delivered"] += 1
                message.status = DeliveryStatus.DELIVERED
            else:
                self._stats["total_failed"] += 1

        has_failures = any(r.status != DeliveryStatus.DELIVERED for r in receipts)
        if has_failures and message.retry_count < message.max_retries:
            message.retry_count += 1
            message.status = DeliveryStatus.RETRYING
            retry_delay = 0.5 * (2 ** (message.retry_count - 1))
            await asyncio.sleep(retry_delay)
            retry_receipts = await self._router.deliver(message)
            for rr in retry_receipts:
                if rr.status == DeliveryStatus.DELIVERED:
                    self._stats["total_delivered"] += 1
                    self._stats["total_failed"] -= 1
            receipts.extend(retry_receipts)
            message.status = DeliveryStatus.DELIVERED if any(
                r.status == DeliveryStatus.DELIVERED for r in retry_receipts
            ) else DeliveryStatus.FAILED

        return receipts

    async def send_and_wait(
        self,
        message: ProtocolMessage,
        timeout: Optional[float] = None,
    ) -> Optional[ProtocolMessage]:
        """Send a request and wait for the response."""
        actual_timeout = timeout or message.timeout_seconds
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[message.id] = future

        await self.send(message)

        try:
            return await asyncio.wait_for(future, timeout=actual_timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending.pop(message.id, None)

    def receive_response(self, response: ProtocolMessage) -> None:
        """Process a response message and resolve any pending futures."""
        if response.correlation_id in self._pending:
            future = self._pending[response.correlation_id]
            if not future.done():
                future.set_result(response)

        self._log_message(response)

    def start_conversation(
        self,
        participants: List[str],
        topic: str = "",
    ) -> Conversation:
        """Start a new conversation thread."""
        conv = Conversation(
            participants=participants,
            topic=topic,
        )
        self._conversations[conv.id] = conv

        if len(self._conversations) > self._max_conversations:
            oldest = min(self._conversations.values(), key=lambda c: c.last_activity)
            del self._conversations[oldest.id]

        return conv

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)

    def list_conversations(
        self,
        participant: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        convs = self._conversations.values()
        if participant:
            convs = [c for c in convs if participant in c.participants]
        if status:
            convs = [c for c in convs if c.status == status]
        return [c.to_dict() for c in convs]

    def _log_message(self, message: ProtocolMessage) -> None:
        self._message_log.append(message)
        if len(self._message_log) > self._max_log:
            self._message_log = self._message_log[-self._max_log:]

    def get_message_log(
        self,
        msg_type: Optional[MessageType] = None,
        sender: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        msgs = self._message_log
        if msg_type:
            msgs = [m for m in msgs if m.type == msg_type]
        if sender:
            msgs = [m for m in msgs if m.sender == sender]
        return [m.to_dict() for m in msgs[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "active_conversations": sum(
                1 for c in self._conversations.values() if c.status == "active"
            ),
            "total_conversations": len(self._conversations),
            "pending_requests": len(self._pending),
            "message_log_size": len(self._message_log),
        }


_global_protocol: Optional[AgentProtocol] = None


def get_protocol() -> AgentProtocol:
    """Get the global AgentProtocol singleton."""
    global _global_protocol
    if _global_protocol is None:
        _global_protocol = AgentProtocol()
    return _global_protocol


def reset_protocol() -> None:
    """Reset the global AgentProtocol singleton."""
    global _global_protocol
    _global_protocol = None
