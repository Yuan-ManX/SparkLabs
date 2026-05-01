"""
SparkLabs Backend - WebSocket Handler with Agent Event Streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        self._counter = 0

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        self._counter += 1
        client_id = f"client_{self._counter}"
        self.active_connections[client_id] = websocket
        logger.info("WebSocket client connected: %s (total: %d)", client_id, len(self.active_connections))
        return client_id

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        for channel_clients in self.channel_subscriptions.values():
            channel_clients.discard(client_id)
        logger.info("WebSocket client disconnected: %s (remaining: %d)", client_id, len(self.active_connections))

    def subscribe(self, client_id: str, channel: str):
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(client_id)

    def unsubscribe(self, client_id: str, channel: str):
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(client_id)

    async def send_to_client(self, client_id: str, message: dict):
        ws = self.active_connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, message: dict, channel: str = "all"):
        clients = self.channel_subscriptions.get(channel, set())
        if channel == "all":
            clients = set(self.active_connections.keys())
        disconnected = []
        for client_id in clients:
            ws = self.active_connections.get(client_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect(cid)

    async def broadcast_agent_event(self, event_type: str, data: dict):
        await self.broadcast({
            "type": "agent_event",
            "event": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0,
        }, channel="agent")

    async def broadcast_engine_status(self, status: dict):
        await self.broadcast({
            "type": "engine_status_update",
            "data": status,
        }, channel="engine")

    async def broadcast_log(self, level: str, message: str):
        await self.broadcast({
            "type": "log",
            "level": level,
            "message": message,
        }, channel="logs")


manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return manager


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    await manager.send_to_client(client_id, {"type": "connected", "client_id": client_id})

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")

                if msg_type == "ping":
                    await manager.send_to_client(client_id, {"type": "pong"})

                elif msg_type == "subscribe":
                    for channel in message.get("channels", ["all"]):
                        manager.subscribe(client_id, channel)
                    await manager.send_to_client(client_id, {
                        "type": "subscribed",
                        "channels": message.get("channels", ["all"]),
                    })

                elif msg_type == "unsubscribe":
                    for channel in message.get("channels", []):
                        manager.unsubscribe(client_id, channel)
                    await manager.send_to_client(client_id, {
                        "type": "unsubscribed",
                        "channels": message.get("channels", []),
                    })

                elif msg_type == "agent_prompt":
                    prompt = message.get("prompt", "")
                    if prompt:
                        try:
                            from sparkai.agent.runtime import get_runtime
                            runtime = get_runtime()
                            if runtime and runtime.is_initialized:
                                result = await runtime.process_prompt(prompt)
                                await manager.broadcast_agent_event("prompt_result", {
                                    "prompt": prompt,
                                    "result": str(result)[:2000] if result else None,
                                })
                            else:
                                await manager.broadcast_agent_event("prompt_result", {
                                    "prompt": prompt,
                                    "status": "Runtime not initialized",
                                })
                        except Exception as e:
                            await manager.broadcast_agent_event("prompt_error", {
                                "prompt": prompt,
                                "error": str(e),
                            })

                elif msg_type == "engine_command":
                    command = message.get("command", "")
                    if command == "start":
                        try:
                            from sparkai.engine.engine import SparkEngine
                            engine = SparkEngine.get_instance()
                            engine.start_world(message.get("world_id", "default"))
                            await manager.broadcast_engine_status(engine.get_status())
                        except Exception as e:
                            await manager.broadcast_agent_event("engine_error", {"error": str(e)})
                    elif command == "stop":
                        try:
                            from sparkai.engine.engine import SparkEngine
                            engine = SparkEngine.get_instance()
                            engine.stop_world(message.get("world_id", "default"))
                            await manager.broadcast_engine_status(engine.get_status())
                        except Exception as e:
                            await manager.broadcast_agent_event("engine_error", {"error": str(e)})

                elif msg_type == "intent_classify":
                    prompt = message.get("prompt", "")
                    if prompt:
                        try:
                            from sparkai.agent.agent_intent_classifier import get_intent_classifier
                            classifier = get_intent_classifier()
                            intent_result = classifier.classify(prompt)
                            await manager.broadcast_agent_event("intent_classified", intent_result.to_dict())
                        except Exception as e:
                            await manager.broadcast_agent_event("intent_error", {"error": str(e)})

                elif msg_type == "budget_check":
                    session_id = message.get("session_id", "")
                    try:
                        from sparkai.agent.agent_execution_budget import get_execution_budget
                        budget = get_execution_budget()
                        tier = budget.check_tier(session_id)
                        stats = budget.get_session_stats(session_id) if session_id else budget.get_overall_stats()
                        await manager.broadcast_agent_event("budget_status", {
                            "session_id": session_id,
                            "tier": tier.value,
                            "stats": stats,
                        })
                    except Exception as e:
                        await manager.broadcast_agent_event("budget_error", {"error": str(e)})

                elif msg_type == "skill_curator":
                    action = message.get("action", "health")
                    try:
                        from sparkai.agent.agent_skill_curator import get_skill_curator
                        curator = get_skill_curator()
                        if action == "health":
                            health = curator.get_ecosystem_health()
                            await manager.broadcast_agent_event("curator_health", health)
                        elif action == "review":
                            result = await curator.review()
                            await manager.broadcast_agent_event("curator_review", result)
                    except Exception as e:
                        await manager.broadcast_agent_event("curator_error", {"error": str(e)})

                else:
                    await manager.send_to_client(client_id, {
                        "type": "echo",
                        "data": message,
                    })

            except json.JSONDecodeError:
                await manager.send_to_client(client_id, {
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
