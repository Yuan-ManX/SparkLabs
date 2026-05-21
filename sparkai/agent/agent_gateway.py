"""
SparkLabs Agent - Gateway

Multi-platform agent interface system that manages connections across web API,
WebSocket, CLI commands, and message-based platforms. Routes agent tasks to
appropriate handlers and maintains connection state with delivery tracking.

Architecture:
  AgentGateway
    |-- GatewayConnection (per-client session state tracking)
    |-- PlatformEndpoint (registered handler definitions)
    |-- RoutedMessage (message envelope with priority/format)
    |-- MessageDelivery (delivery status and acknowledgment log)

Gateway Platforms:
  - WEB_API: HTTP REST endpoints for agent task submission
  - WEBSOCKET: persistent bidirectional streaming connections
  - CLI: terminal-based command execution interface
  - REST: RESTful resource-oriented agent interactions
  - SDK: language-specific SDK integrations for embedded agents
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GatewayPlatform(Enum):
    WEB_API = "web_api"
    WEBSOCKET = "websocket"
    CLI = "cli"
    REST = "rest"
    SDK = "sdk"


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DEGRADED = "degraded"


class MessageFormat(Enum):
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"
    STREAM = "stream"


class RoutePolicy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    PRIORITY = "priority"
    STICKY = "sticky"
    BROADCAST = "broadcast"


@dataclass
class GatewayConnection:
    connection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    platform: GatewayPlatform = GatewayPlatform.WEB_API
    client_id: str = ""
    state: ConnectionState = ConnectionState.DISCONNECTED
    metadata: Dict[str, Any] = field(default_factory=dict)
    connected_at: float = 0.0
    last_heartbeat: float = 0.0
    message_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "platform": self.platform.value,
            "client_id": self.client_id,
            "state": self.state.value,
            "metadata": self.metadata,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "message_count": self.message_count,
            "error_count": self.error_count,
        }


@dataclass
class PlatformEndpoint:
    endpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    platform: GatewayPlatform = GatewayPlatform.WEB_API
    name: str = ""
    handler_type: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    policy: RoutePolicy = RoutePolicy.ROUND_ROBIN
    active_connections: int = 0
    total_routed: int = 0
    registered_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "platform": self.platform.value,
            "name": self.name,
            "handler_type": self.handler_type,
            "config": self.config,
            "policy": self.policy.value,
            "active_connections": self.active_connections,
            "total_routed": self.total_routed,
            "registered_at": self.registered_at,
        }


@dataclass
class RoutedMessage:
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sender_id: str = ""
    target_platform: GatewayPlatform = GatewayPlatform.WEB_API
    target_endpoint: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    format: MessageFormat = MessageFormat.JSON
    correlation_id: str = ""
    created_at: float = field(default_factory=time.time)
    delivered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "target_platform": self.target_platform.value,
            "target_endpoint": self.target_endpoint,
            "payload": self.payload,
            "priority": self.priority,
            "format": self.format.value,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "delivered": self.delivered,
        }


@dataclass
class MessageDelivery:
    delivery_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    message_id: str = ""
    connection_id: str = ""
    status: str = "pending"
    attempt_count: int = 0
    first_attempt_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "message_id": self.message_id,
            "connection_id": self.connection_id,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "first_attempt_at": self.first_attempt_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }


class AgentGateway:
    """Multi-platform agent interface system for connection and message routing."""

    _instance: Optional["AgentGateway"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._connections: Dict[str, GatewayConnection] = {}
        self._endpoints: Dict[str, PlatformEndpoint] = {}
        self._message_queue: List[RoutedMessage] = []
        self._delivery_log: List[MessageDelivery] = []

    @classmethod
    def get_instance(cls) -> "AgentGateway":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Endpoint Registration ----

    def register_endpoint(self,
                          platform: str,
                          name: str,
                          handler_type: str,
                          config: Optional[Dict[str, Any]] = None) -> PlatformEndpoint:
        try:
            gw_platform = GatewayPlatform(platform.lower())
        except ValueError:
            gw_platform = GatewayPlatform.WEB_API

        endpoint = PlatformEndpoint(
            platform=gw_platform,
            name=name,
            handler_type=handler_type,
            config=config or {},
        )
        self._endpoints[endpoint.endpoint_id] = endpoint
        return endpoint

    # ---- Connection Management ----

    def open_connection(self,
                        platform: str,
                        client_id: str,
                        metadata: Optional[Dict[str, Any]] = None) -> GatewayConnection:
        try:
            gw_platform = GatewayPlatform(platform.lower())
        except ValueError:
            gw_platform = GatewayPlatform.WEB_API

        now = time.time()
        connection = GatewayConnection(
            platform=gw_platform,
            client_id=client_id,
            state=ConnectionState.CONNECTED,
            metadata=metadata or {},
            connected_at=now,
            last_heartbeat=now,
        )
        self._connections[connection.connection_id] = connection

        for endpoint in self._endpoints.values():
            if endpoint.platform == gw_platform:
                endpoint.active_connections += 1

        return connection

    def close_connection(self, connection_id: str) -> bool:
        connection = self._connections.pop(connection_id, None)
        if connection is None:
            return False

        connection.state = ConnectionState.DISCONNECTED
        for endpoint in self._endpoints.values():
            if endpoint.platform == connection.platform and endpoint.active_connections > 0:
                endpoint.active_connections -= 1

        return True

    # ---- Message Routing ----

    def route_message(self,
                      sender_id: str,
                      target_platform: str,
                      target_endpoint: str,
                      payload: Dict[str, Any],
                      priority: int = 0,
                      format: str = "json") -> RoutedMessage:
        try:
            gw_platform = GatewayPlatform(target_platform.lower())
        except ValueError:
            gw_platform = GatewayPlatform.WEB_API

        try:
            msg_format = MessageFormat(format.lower())
        except ValueError:
            msg_format = MessageFormat.JSON

        message = RoutedMessage(
            sender_id=sender_id,
            target_platform=gw_platform,
            target_endpoint=target_endpoint,
            payload=payload,
            priority=priority,
            format=msg_format,
        )
        self._message_queue.append(message)

        for endpoint in self._endpoints.values():
            if endpoint.endpoint_id == target_endpoint:
                endpoint.total_routed += 1
                break

        return message

    def broadcast_message(self,
                          payload: Dict[str, Any],
                          platforms: Optional[List[str]] = None,
                          priority: int = 0) -> List[RoutedMessage]:
        target_platforms: List[GatewayPlatform]
        if platforms is None:
            target_platforms = list(GatewayPlatform)
        else:
            target_platforms = []
            for p in platforms:
                try:
                    target_platforms.append(GatewayPlatform(p.lower()))
                except ValueError:
                    pass
        if not target_platforms:
            target_platforms = [GatewayPlatform.WEB_API]

        messages: List[RoutedMessage] = []
        for gw_platform in target_platforms:
            matching = [e for e in self._endpoints.values() if e.platform == gw_platform]
            for endpoint in matching:
                message = self.route_message(
                    sender_id="broadcast",
                    target_platform=gw_platform.value,
                    target_endpoint=endpoint.endpoint_id,
                    payload=payload,
                    priority=priority,
                    format="json",
                )
                messages.append(message)
        return messages

    # ---- Message Delivery ----

    def deliver_message(self, message_id: str) -> MessageDelivery:
        message: Optional[RoutedMessage] = None
        for m in self._message_queue:
            if m.message_id == message_id:
                message = m
                break

        if message is None:
            delivery = MessageDelivery(
                message_id=message_id,
                status="failed",
                error_message="Message not found in queue",
            )
            self._delivery_log.append(delivery)
            return delivery

        matching_connections: List[GatewayConnection] = []
        for conn in self._connections.values():
            if conn.platform == message.target_platform and conn.state == ConnectionState.CONNECTED:
                matching_connections.append(conn)

        connection_id = matching_connections[0].connection_id if matching_connections else ""

        delivery = MessageDelivery(
            message_id=message_id,
            connection_id=connection_id,
            status="delivered",
            attempt_count=1,
            completed_at=time.time(),
        )
        message.delivered = True
        self._delivery_log.append(delivery)
        return delivery

    # ---- Query Methods ----

    def get_active_connections(self, platform: Optional[str] = None) -> List[GatewayConnection]:
        active = [
            c for c in self._connections.values()
            if c.state == ConnectionState.CONNECTED
        ]
        if platform is None:
            return active
        try:
            gw_platform = GatewayPlatform(platform.lower())
        except ValueError:
            return []
        return [c for c in active if c.platform == gw_platform]

    def get_message_queue(self,
                          limit: int = 100,
                          platform: Optional[str] = None) -> List[RoutedMessage]:
        queue = list(self._message_queue)
        if platform is not None:
            try:
                gw_platform = GatewayPlatform(platform.lower())
                queue = [m for m in queue if m.target_platform == gw_platform]
            except ValueError:
                pass
        return queue[:limit]

    def get_delivery_status(self, message_id: str) -> Optional[MessageDelivery]:
        for delivery in self._delivery_log:
            if delivery.message_id == message_id:
                return delivery
        return None

    def get_platform_stats(self, platform: str) -> Dict[str, Any]:
        try:
            gw_platform = GatewayPlatform(platform.lower())
        except ValueError:
            return {"platform": platform, "error": "unknown platform"}

        endpoints_for_platform = [
            e for e in self._endpoints.values() if e.platform == gw_platform
        ]
        connections_for_platform = [
            c for c in self._connections.values() if c.platform == gw_platform
        ]
        active_count = sum(
            1 for c in connections_for_platform if c.state == ConnectionState.CONNECTED
        )
        message_count = sum(
            1 for m in self._message_queue if m.target_platform == gw_platform
        )

        return {
            "platform": gw_platform.value,
            "endpoint_count": len(endpoints_for_platform),
            "total_connections": len(connections_for_platform),
            "active_connections": active_count,
            "queued_messages": message_count,
            "total_routed": sum(e.total_routed for e in endpoints_for_platform),
        }

    def get_stats(self) -> Dict[str, Any]:
        platform_stats: Dict[str, Dict[str, Any]] = {}
        for platform in GatewayPlatform:
            platform_stats[platform.value] = self.get_platform_stats(platform.value)

        delivered_count = sum(1 for m in self._message_queue if m.delivered)
        pending_deliveries = sum(
            1 for d in self._delivery_log if d.status == "pending"
        )

        return {
            "total_endpoints": len(self._endpoints),
            "total_connections": len(self._connections),
            "active_connections": len(self.get_active_connections()),
            "queued_messages": len(self._message_queue),
            "delivered_messages": delivered_count,
            "delivery_log_entries": len(self._delivery_log),
            "pending_deliveries": pending_deliveries,
            "platforms": platform_stats,
        }


def get_gateway() -> AgentGateway:
    return AgentGateway.get_instance()