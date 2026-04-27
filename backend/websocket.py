"""
SparkLabs Backend - WebSocket Handler
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")

                if msg_type == "ping":
                    await manager.send_message({"type": "pong"}, websocket)
                elif msg_type == "engine_status":
                    from sparkai.engine.engine import SparkEngine
                    engine = SparkEngine.get_instance()
                    await manager.send_message({
                        "type": "engine_status",
                        "data": engine.get_status(),
                    }, websocket)
                elif msg_type == "subscribe":
                    await manager.send_message({
                        "type": "subscribed",
                        "channel": message.get("channel", "all"),
                    }, websocket)
                else:
                    await manager.send_message({
                        "type": "echo",
                        "data": message,
                    }, websocket)
            except json.JSONDecodeError:
                await manager.send_message({
                    "type": "error",
                    "message": "Invalid JSON",
                }, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
