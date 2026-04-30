"""
SparkAI Agent - Structured Communication Protocol

Schema-validated inter-agent messaging system that enforces
message contracts, provides dead letter queues for failed
deliveries, and implements backpressure for message flooding.

Architecture:
  StructuredProtocol
    |-- MessageSchema (typed payload validation)
    |-- DeadLetterQueue (failed message recovery)
    |-- BackpressureController (rate limiting and throttling)
    |-- MessageAuditor (delivery tracking and verification)

Message Flow:
  1. Sender creates message with type and payload
  2. Schema validation against registered contract
  3. Backpressure check (rate limit per sender)
  4. Route to recipients
  5. Deliver with confirmation tracking
  6. Failed deliveries go to dead letter queue
  7. Audit log records all operations

Schema Types:
  - task_assignment: Agent task delegation
  - task_result: Task completion notification
  - status_update: Agent state change
  - coordination: Multi-agent coordination
  - approval_request: Human-in-the-loop gate
  - approval_response: Approval decision
  - error_report: Error notification
  - knowledge_share: Inter-agent knowledge transfer
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class MessageType(Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    STATUS_UPDATE = "status_update"
    COORDINATION = "coordination"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    ERROR_REPORT = "error_report"
    KNOWLEDGE_SHARE = "knowledge_share"
    HEARTBEAT = "heartbeat"
    CUSTOM = "custom"


class DeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"


class SchemaValidationResult(Enum):
    VALID = "valid"
    INVALID_TYPE = "invalid_type"
    MISSING_FIELD = "missing_field"
    INVALID_VALUE = "invalid_value"
    UNKNOWN_SCHEMA = "unknown_schema"


@dataclass
class MessageSchema:
    message_type: MessageType = MessageType.CUSTOM
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    field_types: Dict[str, str] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_type": self.message_type.value,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "field_types": self.field_types,
            "description": self.description,
        }


@dataclass
class StructuredMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.CUSTOM
    sender: str = ""
    recipient: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 50
    ttl_seconds: float = 300.0
    created_at: float = field(default_factory=time.time)
    delivered_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    validation_result: Optional[SchemaValidationResult] = None
    retry_count: int = 0
    max_retries: int = 3
    parent_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload_keys": list(self.payload.keys()),
            "priority": self.priority,
            "delivery_status": self.delivery_status.value,
            "validation_result": self.validation_result.value if self.validation_result else None,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "delivered_at": self.delivered_at,
            "correlation_id": self.correlation_id,
        }

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


@dataclass
class DeadLetterEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: Optional[StructuredMessage] = None
    failure_reason: str = ""
    original_recipient: str = ""
    retry_attempted: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "message_id": self.message.id if self.message else None,
            "message_type": self.message.message_type.value if self.message else None,
            "sender": self.message.sender if self.message else None,
            "failure_reason": self.failure_reason,
            "original_recipient": self.original_recipient,
            "retry_attempted": self.retry_attempted,
            "created_at": self.created_at,
        }


@dataclass
class BackpressureConfig:
    max_messages_per_second: float = 100.0
    max_messages_per_sender: int = 50
    burst_allowance: int = 10
    cooldown_seconds: float = 1.0


class SchemaValidator:
    """
    Validates message payloads against registered schemas.
    Each message type has a contract defining required fields
    and expected field types.
    """

    def __init__(self):
        self._schemas: Dict[MessageType, MessageSchema] = {}
        self._seed_schemas()

    def _seed_schemas(self) -> None:
        schemas = [
            MessageSchema(
                message_type=MessageType.TASK_ASSIGNMENT,
                required_fields=["task_id", "task_description", "assigned_role"],
                optional_fields=["priority", "deadline", "context", "parent_task_id"],
                field_types={"task_id": "str", "task_description": "str", "assigned_role": "str", "priority": "int"},
                description="Agent task delegation message",
            ),
            MessageSchema(
                message_type=MessageType.TASK_RESULT,
                required_fields=["task_id", "status", "result_summary"],
                optional_fields=["artifacts", "metrics", "error_details"],
                field_types={"task_id": "str", "status": "str", "result_summary": "str"},
                description="Task completion notification",
            ),
            MessageSchema(
                message_type=MessageType.STATUS_UPDATE,
                required_fields=["agent_id", "new_state"],
                optional_fields=["reason", "progress", "metadata"],
                field_types={"agent_id": "str", "new_state": "str"},
                description="Agent state change notification",
            ),
            MessageSchema(
                message_type=MessageType.COORDINATION,
                required_fields=["coordinator_id", "action", "participants"],
                optional_fields=["strategy", "deadline", "constraints"],
                field_types={"coordinator_id": "str", "action": "str", "participants": "list"},
                description="Multi-agent coordination message",
            ),
            MessageSchema(
                message_type=MessageType.APPROVAL_REQUEST,
                required_fields=["requester_id", "operation", "justification"],
                optional_fields=["risk_level", "impact_scope", "alternatives"],
                field_types={"requester_id": "str", "operation": "str", "justification": "str"},
                description="Human-in-the-loop approval gate",
            ),
            MessageSchema(
                message_type=MessageType.APPROVAL_RESPONSE,
                required_fields=["request_id", "decision", "reviewer_id"],
                optional_fields=["conditions", "comments"],
                field_types={"request_id": "str", "decision": "str", "reviewer_id": "str"},
                description="Approval decision response",
            ),
            MessageSchema(
                message_type=MessageType.ERROR_REPORT,
                required_fields=["error_type", "error_message", "source"],
                optional_fields=["stack_trace", "context", "severity"],
                field_types={"error_type": "str", "error_message": "str", "source": "str"},
                description="Error notification message",
            ),
            MessageSchema(
                message_type=MessageType.KNOWLEDGE_SHARE,
                required_fields=["knowledge_type", "content", "confidence"],
                optional_fields=["source_agent", "tags", "expiry"],
                field_types={"knowledge_type": "str", "content": "str", "confidence": "float"},
                description="Inter-agent knowledge transfer",
            ),
        ]
        for schema in schemas:
            self._schemas[schema.message_type] = schema

    def register_schema(self, schema: MessageSchema) -> None:
        self._schemas[schema.message_type] = schema

    def validate(self, message: StructuredMessage) -> SchemaValidationResult:
        schema = self._schemas.get(message.message_type)
        if not schema:
            return SchemaValidationResult.UNKNOWN_SCHEMA

        for req_field in schema.required_fields:
            if req_field not in message.payload:
                return SchemaValidationResult.MISSING_FIELD

        for field_name, expected_type in schema.field_types.items():
            if field_name in message.payload:
                value = message.payload[field_name]
                actual_type = type(value).__name__
                type_map = {"str": ("str",), "int": ("int",), "float": ("float", "int"), "list": ("list", "tuple"), "dict": ("dict",), "bool": ("bool",)}
                allowed = type_map.get(expected_type, (expected_type,))
                if actual_type not in allowed:
                    return SchemaValidationResult.INVALID_VALUE

        return SchemaValidationResult.VALID


class BackpressureController:
    """
    Rate limiting and throttling for message delivery.
    Prevents message flooding from overwhelming handlers.
    """

    def __init__(self, config: Optional[BackpressureConfig] = None):
        self._config = config or BackpressureConfig()
        self._sender_counts: Dict[str, List[float]] = {}
        self._global_timestamps: List[float] = []
        self._throttled_senders: Dict[str, float] = {}

    def allow(self, sender: str) -> bool:
        now = time.time()

        if sender in self._throttled_senders:
            if now - self._throttled_senders[sender] < self._config.cooldown_seconds:
                return False
            del self._throttled_senders[sender]

        self._global_timestamps = [t for t in self._global_timestamps if now - t < 1.0]
        if len(self._global_timestamps) >= self._config.max_messages_per_second:
            return False

        sender_times = self._sender_counts.get(sender, [])
        sender_times = [t for t in sender_times if now - t < 1.0]
        if len(sender_times) >= self._config.max_messages_per_sender:
            self._throttled_senders[sender] = now
            return False

        sender_times.append(now)
        self._sender_counts[sender] = sender_times
        self._global_timestamps.append(now)
        return True

    def get_stats(self) -> Dict[str, Any]:
        return {
            "throttled_senders": len(self._throttled_senders),
            "global_rate_1s": len(self._global_timestamps),
            "max_per_second": self._config.max_messages_per_second,
        }


class StructuredProtocol:
    """
    Schema-validated inter-agent messaging system with dead letter
    queues, backpressure control, and delivery auditing.

    Usage:
        protocol = StructuredProtocol()
        msg = protocol.create_message(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender="director",
            recipient="lead_programmer",
            payload={"task_id": "t1", "task_description": "Build physics", "assigned_role": "specialist"}
        )
        result = protocol.send(msg)
    """

    def __init__(self, backpressure_config: Optional[BackpressureConfig] = None):
        self._validator = SchemaValidator()
        self._backpressure = BackpressureController(backpressure_config)
        self._dead_letter_queue: List[DeadLetterEntry] = []
        self._handlers: Dict[str, Callable] = {}
        self._type_handlers: Dict[MessageType, List[str]] = {}
        self._messages: Dict[str, StructuredMessage] = {}
        self._delivery_log: List[Dict[str, Any]] = []
        self._stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "total_dead_lettered": 0,
            "validation_failures": 0,
            "backpressure_rejections": 0,
        }

    def create_message(self, message_type: MessageType, sender: str, recipient: str, payload: Dict[str, Any], priority: int = 50, correlation_id: Optional[str] = None) -> StructuredMessage:
        msg = StructuredMessage(
            message_type=message_type,
            sender=sender,
            recipient=recipient,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
        )
        return msg

    def send(self, message: StructuredMessage) -> Dict[str, Any]:
        self._stats["total_sent"] += 1

        validation = self._validator.validate(message)
        message.validation_result = validation
        if validation != SchemaValidationResult.VALID:
            self._stats["validation_failures"] += 1
            self._dead_letter(message, f"Schema validation failed: {validation.value}")
            return {"status": "validation_failed", "result": validation.value}

        if not self._backpressure.allow(message.sender):
            self._stats["backpressure_rejections"] += 1
            self._dead_letter(message, "Backpressure limit exceeded")
            return {"status": "backpressure_rejected"}

        self._messages[message.id] = message

        handler_ids = self._type_handlers.get(message.message_type, [])
        if message.recipient in self._handlers:
            handler_ids = [message.recipient]

        if not handler_ids:
            message.delivery_status = DeliveryStatus.FAILED
            self._dead_letter(message, "No handler registered for recipient")
            return {"status": "no_handler", "message_id": message.id}

        delivered = False
        for handler_id in handler_ids:
            handler = self._handlers.get(handler_id)
            if handler:
                try:
                    handler(message)
                    delivered = True
                except Exception as e:
                    self._dead_letter(message, f"Handler error: {e}")

        if delivered:
            message.delivery_status = DeliveryStatus.DELIVERED
            message.delivered_at = time.time()
            self._stats["total_delivered"] += 1
        else:
            self._dead_letter(message, "All handlers failed")
            return {"status": "delivery_failed", "message_id": message.id}

        self._delivery_log.append({
            "message_id": message.id,
            "type": message.message_type.value,
            "sender": message.sender,
            "recipient": message.recipient,
            "status": message.delivery_status.value,
            "timestamp": time.time(),
        })

        return {"status": "delivered", "message_id": message.id}

    def register_handler(self, handler_id: str, handler: Callable, message_types: Optional[List[MessageType]] = None) -> None:
        self._handlers[handler_id] = handler
        if message_types:
            for mt in message_types:
                self._type_handlers.setdefault(mt, []).append(handler_id)

    def acknowledge(self, message_id: str) -> bool:
        msg = self._messages.get(message_id)
        if msg and msg.delivery_status == DeliveryStatus.DELIVERED:
            msg.delivery_status = DeliveryStatus.ACKNOWLEDGED
            msg.acknowledged_at = time.time()
            return True
        return False

    def _dead_letter(self, message: StructuredMessage, reason: str) -> None:
        self._stats["total_dead_lettered"] += 1
        message.delivery_status = DeliveryStatus.DEAD_LETTER
        entry = DeadLetterEntry(
            message=message,
            failure_reason=reason,
            original_recipient=message.recipient,
        )
        self._dead_letter_queue.append(entry)

    def retry_dead_letter(self, entry_id: str) -> Dict[str, Any]:
        entry = next((e for e in self._dead_letter_queue if e.id == entry_id), None)
        if not entry or not entry.message:
            return {"status": "not_found"}

        if entry.retry_attempted:
            return {"status": "already_retried"}

        entry.retry_attempted = True
        new_msg = self.create_message(
            message_type=entry.message.message_type,
            sender=entry.message.sender,
            recipient=entry.message.recipient,
            payload=entry.message.payload,
            priority=entry.message.priority,
        )
        return self.send(new_msg)

    def get_dead_letters(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._dead_letter_queue[-limit:]]

    def get_delivery_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._delivery_log[-limit:]

    def list_schemas(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._validator._schemas.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "registered_handlers": len(self._handlers),
            "dead_letter_count": len(self._dead_letter_queue),
            "backpressure": self._backpressure.get_stats(),
            "delivery_rate": self._stats["total_delivered"] / max(self._stats["total_sent"], 1),
        }


_global_structured_protocol: Optional[StructuredProtocol] = None


def get_structured_protocol() -> StructuredProtocol:
    global _global_structured_protocol
    if _global_structured_protocol is None:
        _global_structured_protocol = StructuredProtocol()
    return _global_structured_protocol
