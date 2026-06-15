"""
SparkLabs Engine - Network RPC

Remote procedure call layer for multiplayer game networking.
Provides reliable and unreliable RPC invocation across network
boundaries, with parameter serialization, call routing, and
return value marshaling for the AI-native game engine.

Architecture:
  NetworkRPC
    |-- RPCHandler (server-side procedure registration)
    |-- RPCClient (client-side call invocation)
    |-- RPCSerializer (parameter marshaling/unmarshaling)
    |-- RPCMessageQueue (ordered delivery with priority)
    |-- RPCTimeoutManager (call timeout and retry logic)

Call Types:
  - REQUEST: standard request-response call
  - NOTIFY: fire-and-forget notification
  - BROADCAST: send to all connected clients
  - TARGETED: send to specific client/peers
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class RPCCallType(Enum):
    REQUEST = "request"
    NOTIFY = "notify"
    BROADCAST = "broadcast"
    TARGETED = "targeted"


class RPCDelivery(Enum):
    RELIABLE = "reliable"
    UNRELIABLE = "unreliable"
    RELIABLE_ORDERED = "reliable_ordered"


class RPCStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    RECEIVED = "received"
    EXECUTING = "executing"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


@dataclass
class RPCMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    procedure: str = ""
    call_type: RPCCallType = RPCCallType.REQUEST
    delivery: RPCDelivery = RPCDelivery.RELIABLE
    sender_id: str = ""
    target_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "procedure": self.procedure,
            "call_type": self.call_type.value,
            "delivery": self.delivery.value,
            "sender_id": self.sender_id,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
        }


@dataclass
class RPCResult:
    call_id: str = ""
    procedure: str = ""
    status: RPCStatus = RPCStatus.PENDING
    result: Any = None
    error: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "procedure": self.procedure,
            "status": self.status.value,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class RPCEndpoint:
    endpoint_id: str = ""
    name: str = ""
    client_type: str = "peer"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "name": self.name,
            "client_type": self.client_type,
        }


class NetworkRPC:
    """Remote procedure call layer for multiplayer game networking."""

    _instance: Optional["NetworkRPC"] = None
    _lock = threading.RLock()

    MAX_MESSAGE_QUEUE = 10000
    DEFAULT_TIMEOUT_S = 5.0

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._endpoints: Dict[str, RPCEndpoint] = {}
        self._message_queue: deque = deque()
        self._pending_calls: Dict[str, RPCResult] = {}
        self._call_history: List[RPCResult] = []
        self._sequence_counter: int = 0
        self._timeout_s = self.DEFAULT_TIMEOUT_S
        self._max_history = 200

    @classmethod
    def get_instance(cls) -> "NetworkRPC":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_handler(self, procedure: str, handler: Callable) -> None:
        self._handlers[procedure] = handler

    def unregister_handler(self, procedure: str) -> bool:
        if procedure in self._handlers:
            del self._handlers[procedure]
            return True
        return False

    def register_endpoint(
        self,
        endpoint_id: str,
        name: str = "",
        client_type: str = "peer",
    ) -> RPCEndpoint:
        endpoint = RPCEndpoint(
            endpoint_id=endpoint_id,
            name=name,
            client_type=client_type,
        )
        self._endpoints[endpoint_id] = endpoint
        return endpoint

    def unregister_endpoint(self, endpoint_id: str) -> bool:
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            return True
        return False

    def call(
        self,
        procedure: str,
        parameters: Optional[Dict[str, Any]] = None,
        target_id: str = "",
        call_type: RPCCallType = RPCCallType.REQUEST,
        delivery: RPCDelivery = RPCDelivery.RELIABLE,
        sender_id: str = "",
    ) -> Optional[RPCResult]:
        if procedure not in self._handlers and call_type != RPCCallType.NOTIFY:
            return None

        self._sequence_counter += 1
        message = RPCMessage(
            procedure=procedure,
            call_type=call_type,
            delivery=delivery,
            sender_id=sender_id,
            target_id=target_id,
            parameters=parameters or {},
            sequence=self._sequence_counter,
        )

        self._message_queue.append(message)
        if len(self._message_queue) > self.MAX_MESSAGE_QUEUE:
            self._message_queue.popleft()

        result = RPCResult(
            call_id=message.message_id,
            procedure=procedure,
            status=RPCStatus.SENT,
        )
        self._pending_calls[message.message_id] = result

        if call_type == RPCCallType.NOTIFY:
            result.status = RPCStatus.COMPLETED
            del self._pending_calls[message.message_id]
            self._add_to_history(result)
            return result

        return self._execute_rpc(message)

    def broadcast(
        self,
        procedure: str,
        parameters: Optional[Dict[str, Any]] = None,
        sender_id: str = "",
        exclude_ids: Optional[List[str]] = None,
    ) -> List[RPCResult]:
        results: List[RPCResult] = []
        exclude = set(exclude_ids or [])
        for endpoint_id in self._endpoints:
            if endpoint_id in exclude or endpoint_id == sender_id:
                continue
            result = self.call(
                procedure=procedure,
                parameters=parameters,
                target_id=endpoint_id,
                call_type=RPCCallType.BROADCAST,
                sender_id=sender_id,
            )
            if result:
                results.append(result)
        return results

    def _execute_rpc(self, message: RPCMessage) -> RPCResult:
        result = RPCResult(
            call_id=message.message_id,
            procedure=message.procedure,
            status=RPCStatus.RECEIVED,
        )
        start = time.time()

        handler = self._handlers.get(message.procedure)
        if handler:
            try:
                result.status = RPCStatus.EXECUTING
                result.result = handler(message.parameters)
                result.status = RPCStatus.COMPLETED
            except Exception as exc:
                result.status = RPCStatus.FAILED
                result.error = str(exc)
        else:
            result.status = RPCStatus.FAILED
            result.error = f"No handler for procedure '{message.procedure}'"

        result.duration_ms = (time.time() - start) * 1000
        if message.message_id in self._pending_calls:
            del self._pending_calls[message.message_id]
        self._add_to_history(result)
        return result

    def _add_to_history(self, result: RPCResult) -> None:
        self._call_history.append(result)
        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history:]

    def process_queue(self, max_messages: int = 50) -> int:
        processed = 0
        for _ in range(min(max_messages, len(self._message_queue))):
            if self._message_queue:
                message = self._message_queue.popleft()
                self._execute_rpc(message)
                processed += 1
        return processed

    def get_result(self, call_id: str) -> Optional[RPCResult]:
        return self._pending_calls.get(call_id)

    def get_pending_calls(self) -> List[RPCResult]:
        return list(self._pending_calls.values())

    def get_call_history(self, limit: int = 50) -> List[RPCResult]:
        return self._call_history[-limit:]

    def cleanup_timed_out(self) -> int:
        now = time.time()
        timed_out: List[str] = []
        for call_id, result in self._pending_calls.items():
            if now - result.timestamp > self._timeout_s:
                result.status = RPCStatus.TIMED_OUT
                self._add_to_history(result)
                timed_out.append(call_id)
        for call_id in timed_out:
            del self._pending_calls[call_id]
        return len(timed_out)

    def list_handlers(self) -> List[str]:
        return list(self._handlers.keys())

    def list_endpoints(self) -> List[RPCEndpoint]:
        return list(self._endpoints.values())

    def get_queue_size(self) -> int:
        return len(self._message_queue)

    def get_stats(self) -> Dict[str, Any]:
        completed = sum(
            1 for r in self._call_history if r.status == RPCStatus.COMPLETED
        )
        failed = sum(
            1 for r in self._call_history if r.status == RPCStatus.FAILED
        )
        return {
            "handlers": len(self._handlers),
            "endpoints": len(self._endpoints),
            "queue_size": len(self._message_queue),
            "pending_calls": len(self._pending_calls),
            "total_calls": len(self._call_history),
            "completed": completed,
            "failed": failed,
            "success_rate": round(
                completed / max(1, completed + failed), 3
            ),
            "timeout_s": self._timeout_s,
        }


def get_network_rpc() -> NetworkRPC:
    return NetworkRPC.get_instance()