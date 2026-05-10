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

                elif msg_type == "game_loop_tick":
                    from sparkai.engine.game_loop import get_game_loop
                    gl = get_game_loop()
                    stats = gl.tick()
                    await manager.broadcast_engine_status({"game_loop": stats})

                elif msg_type == "game_loop_control":
                    from sparkai.engine.game_loop import get_game_loop
                    gl = get_game_loop()
                    action = message.get("action", "start")
                    if action == "start":
                        gl.start()
                    elif action == "stop":
                        gl.stop()
                    elif action == "pause":
                        gl.pause()
                    elif action == "resume":
                        gl.resume()
                    await manager.broadcast_engine_status({"game_loop": gl.get_statistics()})

                elif msg_type == "signal_emit":
                    from sparkai.engine.signal_system import get_signal_bus
                    sb = get_signal_bus()
                    signal_name = message.get("signal", "")
                    signal_data = message.get("data", None)
                    count = sb.emit(signal_name, signal_data)
                    await manager.send_to_client(client_id, {
                        "type": "signal_result",
                        "signal": signal_name,
                        "listeners": count,
                    })

                elif msg_type == "animation_control":
                    from sparkai.engine.animation_system import get_animation_player
                    ap = get_animation_player()
                    action = message.get("action", "play")
                    clip_name = message.get("clip", "")
                    if action == "play":
                        ap.play(clip_name)
                    elif action == "pause":
                        ap.pause()
                    elif action == "stop":
                        ap.stop()
                    elif action == "seek":
                        ap.seek(message.get("time", 0.0))
                    await manager.broadcast_engine_status({"animation": ap.get_status()})

                elif msg_type == "collision_query":
                    from sparkai.engine.collision_system import get_collision_system
                    cs = get_collision_system()
                    await manager.send_to_client(client_id, {
                        "type": "collision_data",
                        "colliders": len(cs._colliders),
                        "events": cs._active_events[-20:],
                    })

                elif msg_type == "input_simulate":
                    from sparkai.engine.input_manager import get_input_manager
                    im = get_input_manager()
                    key = message.get("key", "")
                    pressed = message.get("pressed", True)
                    if key:
                        if pressed:
                            im.simulate_key_press(key)
                        else:
                            im.simulate_key_release(key)
                    await manager.broadcast_engine_status({"input": im.get_snapshot()})

                elif msg_type == "approval_request":
                    from sparkai.agent.agent_approval_engine import get_approval_engine
                    ae = get_approval_engine()
                    result = ae.request_approval(
                        action=message.get("action", ""),
                        level=message.get("level", "medium"),
                        session_id=message.get("session_id", "default"),
                        context=message.get("context"),
                    )
                    await manager.send_to_client(client_id, {
                        "type": "approval_result",
                        "data": result,
                    })

                elif msg_type == "approval_resolve":
                    from sparkai.agent.agent_approval_engine import get_approval_engine
                    ae = get_approval_engine()
                    resolved = ae.resolve_pending(
                        message.get("action", ""),
                        message.get("choice", "approve"),
                        message.get("resolve_all", False),
                    )
                    await manager.broadcast_agent_event("approval_resolved", {"resolved": resolved})

                elif msg_type == "checkpoint_create":
                    from sparkai.agent.agent_checkpoint_manager import get_checkpoint_manager
                    cm = get_checkpoint_manager()
                    cid = cm.create_checkpoint(
                        session_id=message.get("session_id", "default"),
                        state=message.get("state", {}),
                        reason=message.get("reason", "ws"),
                    )
                    cp = cm.get_checkpoint(message.get("session_id", "default"), cid)
                    await manager.send_to_client(client_id, {
                        "type": "checkpoint_created",
                        "checkpoint_id": cid,
                        "detail": cp,
                    })

                elif msg_type == "checkpoint_rollback":
                    from sparkai.agent.agent_checkpoint_manager import get_checkpoint_manager
                    cm = get_checkpoint_manager()
                    rolled = cm.rollback(
                        message.get("session_id", "default"),
                        message.get("checkpoint_id", ""),
                    )
                    await manager.send_to_client(client_id, {
                        "type": "checkpoint_rolled_back",
                        "success": rolled is not None,
                        "session_id": message.get("session_id", "default"),
                    })

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

                elif msg_type == "evaluator":
                    action = message.get("action", "rubrics")
                    try:
                        from sparkai.agent.agent_self_evaluator import get_self_evaluator
                        e = get_self_evaluator()
                        if action == "rubrics":
                            await manager.send_to_client(client_id, {"type": "evaluator_rubrics", "data": e.list_rubric_types()})
                        elif action == "evaluate":
                            result = e.evaluate(message.get("content", ""), message.get("content_type", "game_design"), message.get("metadata"))
                            await manager.send_to_client(client_id, {"type": "evaluator_result", "data": {"score": result.overall_score}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "evaluator_error", "error": str(e)})

                elif msg_type == "planner":
                    action = message.get("action", "templates")
                    try:
                        from sparkai.agent.agent_strategic_planner import get_strategic_planner
                        p = get_strategic_planner()
                        if action == "templates":
                            await manager.send_to_client(client_id, {"type": "planner_templates", "data": p.list_templates()})
                        elif action == "create_plan":
                            plan = p.create_plan(message.get("goal", ""), message.get("game_type", "2d_platformer"), message.get("max_depth", 5))
                            await manager.send_to_client(client_id, {"type": "planner_plan", "data": {"plan_id": plan.plan_id, "tasks": len(plan.tasks)}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "planner_error", "error": str(e)})

                elif msg_type == "circuit":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_circuit_breaker import get_circuit_breaker
                        cb = get_circuit_breaker()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "circuit_stats", "data": cb.get_stats()})
                        elif action == "reset":
                            cb.reset()
                            await manager.send_to_client(client_id, {"type": "circuit_reset", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "circuit_error", "error": str(e)})

                elif msg_type == "persona":
                    action = message.get("action", "list")
                    try:
                        from sparkai.agent.agent_persona import get_persona_system
                        ps = get_persona_system()
                        if action == "list":
                            await manager.send_to_client(client_id, {"type": "persona_list", "data": ps.list_personas()})
                        elif action == "assign":
                            persona = ps.assign_persona(message.get("role", "game_designer"), message.get("session_id", "default"))
                            await manager.send_to_client(client_id, {"type": "persona_assigned", "data": {"role": persona.display_name}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "persona_error", "error": str(e)})

                elif msg_type == "camera":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.camera_system import get_camera_system
                        c = get_camera_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "camera_stats", "data": c.get_stats()})
                        elif action == "position":
                            c.set_position(message.get("x", 0.0), message.get("y", 0.0))
                            await manager.send_to_client(client_id, {"type": "camera_position", "data": {"x": c.x, "y": c.y}})
                        elif action == "follow":
                            c.follow(message.get("entity_id", ""), message.get("smoothing", 0.1))
                            await manager.send_to_client(client_id, {"type": "camera_follow", "data": {"entity_id": message.get("entity_id", "")}})
                        elif action == "shake":
                            c.shake(message.get("intensity", 0.5), message.get("duration", 0.3))
                            await manager.send_to_client(client_id, {"type": "camera_shake", "data": {"shaking": True}})
                        elif action == "zoom":
                            c.set_zoom(message.get("zoom", 1.0))
                            await manager.send_to_client(client_id, {"type": "camera_zoom", "data": {"zoom": c.zoom}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "camera_error", "error": str(e)})

                elif msg_type == "serializer":
                    action = message.get("action", "info")
                    try:
                        from sparkai.engine.serialization import get_serializer
                        s = get_serializer()
                        if action == "info":
                            await manager.send_to_client(client_id, {"type": "serializer_info", "data": s.get_schema_info()})
                        elif action == "serialize":
                            result = s.serialize_scene(message.get("data", {}))
                            await manager.send_to_client(client_id, {"type": "serializer_result", "data": {"result": result}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "serializer_error", "error": str(e)})

                elif msg_type == "ui":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.ui_system import get_ui_system
                        u = get_ui_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "ui_stats", "data": u.get_stats()})
                        elif action == "widgets":
                            await manager.send_to_client(client_id, {"type": "ui_widgets", "data": u.get_all_widgets()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "ui_error", "error": str(e)})

                elif msg_type == "layers":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.layer_system import get_layer_system
                        l = get_layer_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "layers_stats", "data": l.get_stats()})
                        elif action == "list":
                            await manager.send_to_client(client_id, {"type": "layers_list", "data": l.get_all_layers()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "layers_error", "error": str(e)})

                elif msg_type == "profiler":
                    action = message.get("action", "snapshot")
                    try:
                        from sparkai.engine.profiler import get_profiler
                        pr = get_profiler()
                        if action == "snapshot":
                            await manager.send_to_client(client_id, {"type": "profiler_snapshot", "data": pr.get_snapshot()})
                        elif action == "report":
                            report = pr.generate_report()
                            await manager.send_to_client(client_id, {"type": "profiler_report", "data": {"avg_fps": report.avg_fps}})
                        elif action == "bottlenecks":
                            await manager.send_to_client(client_id, {"type": "profiler_bottlenecks", "data": pr.detect_bottlenecks()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "profiler_error", "error": str(e)})

                elif msg_type == "streaming":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_streaming import get_streaming_manager
                        sm = get_streaming_manager()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "streaming_stats", "data": sm.get_stats()})
                        elif action == "start":
                            sm.start()
                            await manager.broadcast_agent_event("streaming_started", {"state": sm.state.name.lower()})
                        elif action == "stop":
                            sm.stop()
                            await manager.broadcast_agent_event("streaming_stopped", {"state": sm.state.name.lower()})
                        elif action == "pause":
                            sm.pause()
                            await manager.broadcast_agent_event("streaming_paused", {})
                        elif action == "resume":
                            sm.resume()
                            await manager.broadcast_agent_event("streaming_resumed", {})
                        elif action == "cancel":
                            sm.cancel(message.get("reason", "ws"))
                            await manager.broadcast_agent_event("streaming_cancelled", {})
                        elif action == "partial":
                            await manager.send_to_client(client_id, {"type": "streaming_partial", "data": sm.get_partial()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "streaming_error", "error": str(e)})

                elif msg_type == "delegation":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_delegation import get_delegation_system
                        ds = get_delegation_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "delegation_stats", "data": ds.get_stats()})
                        elif action == "spawn":
                            result = await ds.spawn(message.get("task", ""), message.get("agent_config"), message.get("timeout", 60.0))
                            await manager.send_to_client(client_id, {"type": "delegation_result", "data": result.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "delegation_error", "error": str(e)})

                elif msg_type == "mcp":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_mcp_bridge import get_mcp_bridge
                        mb = get_mcp_bridge()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "mcp_stats", "data": mb.get_stats()})
                        elif action == "servers":
                            await manager.send_to_client(client_id, {"type": "mcp_servers", "data": mb.list_servers()})
                        elif action == "tools":
                            sid = message.get("server_id", "")
                            tools = mb.list_tools(sid) if sid else mb.list_all_tools()
                            await manager.send_to_client(client_id, {"type": "mcp_tools", "data": tools})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "mcp_error", "error": str(e)})

                elif msg_type == "parallel":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_parallel_executor import get_parallel_executor
                        pe = get_parallel_executor()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "parallel_stats", "data": pe.get_stats()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "parallel_error", "error": str(e)})

                elif msg_type == "event_scripting":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.event_scripting import get_event_scripting_system
                        es = get_event_scripting_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "event_scripting_stats", "data": es.get_stats()})
                        elif action == "sheets":
                            await manager.send_to_client(client_id, {"type": "event_scripting_sheets", "data": es.list_sheets()})
                        elif action == "run_all":
                            es.run_all(0.016, message.get("context", {}))
                            await manager.broadcast_agent_event("event_scripting_ran", {})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "event_scripting_error", "error": str(e)})

                elif msg_type == "scene_tree":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.scene_tree import get_scene_tree
                        st = get_scene_tree()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "scene_tree_stats", "data": st.get_stats()})
                        elif action == "groups":
                            await manager.send_to_client(client_id, {"type": "scene_tree_groups", "data": list(st._groups.keys())})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "scene_tree_error", "error": str(e)})

                elif msg_type == "shader":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.shader_system import get_shader_system
                        ss = get_shader_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "shader_stats", "data": ss.get_stats()})
                        elif action == "programs":
                            await manager.send_to_client(client_id, {"type": "shader_programs", "data": list(ss._programs.keys())})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "shader_error", "error": str(e)})

                elif msg_type == "variables":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.variable_system import get_variable_system
                        vs = get_variable_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "variables_stats", "data": vs.get_stats()})
                        elif action == "get":
                            val = vs.get(message.get("name", ""), None)
                            await manager.send_to_client(client_id, {"type": "variables_value", "data": {"name": message.get("name", ""), "value": val}})
                        elif action == "set":
                            vs.set(message.get("name", ""), message.get("value"), None)
                            await manager.send_to_client(client_id, {"type": "variables_set", "data": {"name": message.get("name", ""), "success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "variables_error", "error": str(e)})

                elif msg_type == "resource_loader":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.resource_loader import get_resource_loader
                        rl = get_resource_loader()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "resource_loader_stats", "data": rl.get_stats()})
                        elif action == "cache":
                            await manager.send_to_client(client_id, {"type": "resource_loader_cache", "data": rl.get_cache_stats()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "resource_loader_error", "error": str(e)})

                elif msg_type == "content_safety":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_content_safety import get_content_safety
                        cs = get_content_safety()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "content_safety_stats", "data": cs.get_stats()})
                        elif action == "scan":
                            result = cs.scan(message.get("text", ""), redact=message.get("redact", True))
                            await manager.send_to_client(client_id, {"type": "content_safety_scan", "data": result.to_dict()})
                        elif action == "sanitize":
                            cleaned = cs.sanitize(message.get("text", ""))
                            await manager.send_to_client(client_id, {"type": "content_safety_sanitized", "data": {"sanitized": cleaned}})
                        elif action == "check":
                            is_safe, violations = cs.is_safe(message.get("text", ""))
                            await manager.send_to_client(client_id, {"type": "content_safety_check", "data": {"safe": is_safe, "violations": violations}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "content_safety_error", "error": str(e)})

                elif msg_type == "title_generator":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_title_generator import get_title_generator, TitleContext, TitleStyle
                        tg = get_title_generator()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "title_generator_stats", "data": tg.get_stats()})
                        elif action == "generate":
                            st = message.get("style", "descriptive").upper()
                            ctx = TitleContext(content=message.get("content", ""),
                                              style=TitleStyle[st] if st in TitleStyle.__members__ else TitleStyle.DESCRIPTIVE,
                                              max_length=message.get("max_length", 80))
                            title = tg.generate(ctx)
                            await manager.send_to_client(client_id, {"type": "title_generated", "data": {"title": title}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "title_generator_error", "error": str(e)})

                elif msg_type == "shell_hooks":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_shell_hooks import get_shell_hooks, ShellCommand
                        sh = get_shell_hooks()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "shell_hooks_stats", "data": sh.get_stats()})
                        elif action == "execute":
                            cmd = ShellCommand(command=message.get("command", ""),
                                              args=message.get("args", []),
                                              cwd=message.get("cwd", None),
                                              timeout=message.get("timeout", 30.0))
                            result = sh.execute(cmd)
                            await manager.send_to_client(client_id, {"type": "shell_executed", "data": result.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "shell_hooks_error", "error": str(e)})

                elif msg_type == "skill_preprocessor":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_skill_preprocessor import get_skill_preprocessor
                        sp = get_skill_preprocessor()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "skill_preprocessor_stats", "data": sp.get_stats()})
                        elif action == "validate":
                            report = sp.validate(message.get("skill_id", ""), message.get("params", {}))
                            await manager.send_to_client(client_id, {"type": "skill_validated", "data": report.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "skill_preprocessor_error", "error": str(e)})

                elif msg_type == "inventory":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.inventory_system import get_inventory_system
                        inv_sys = get_inventory_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "inventory_stats", "data": inv_sys.get_stats()})
                        elif action == "get":
                            inv = inv_sys.get_inventory(message.get("owner_id", ""))
                            if inv:
                                await manager.send_to_client(client_id, {"type": "inventory_data", "data": inv.to_dict()})
                            else:
                                await manager.send_to_client(client_id, {"type": "inventory_error", "error": "Not found"})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "inventory_error", "error": str(e)})

                elif msg_type == "localization":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.localization_system import get_localization_system
                        loc = get_localization_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "localization_stats", "data": loc.get_stats()})
                        elif action == "get":
                            text = loc.get_string(message.get("key", ""), variables=message.get("variables"))
                            await manager.send_to_client(client_id, {"type": "localization_string", "data": {"key": message.get("key", ""), "text": text}})
                        elif action == "set_language":
                            from sparkai.engine.localization_system import Language
                            try:
                                lang = Language[message.get("language", "EN").upper()]
                                loc.set_language(lang)
                                await manager.broadcast_agent_event("language_changed", {"language": lang.iso_code})
                            except KeyError:
                                pass
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "localization_error", "error": str(e)})

                elif msg_type == "achievement":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.achievement_system import get_achievement_system
                        ach = get_achievement_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "achievement_stats", "data": ach.get_stats()})
                        elif action == "increment":
                            unlocked = ach.increment_stat(message.get("owner_id", ""),
                                                         message.get("stat_name", ""),
                                                         message.get("amount", 1.0))
                            if unlocked:
                                await manager.broadcast_agent_event("achievement_unlocked",
                                    {"owner_id": message.get("owner_id", ""),
                                     "achievements": [a.name for a in unlocked]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "achievement_error", "error": str(e)})

                elif msg_type == "cloud_sync":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.cloud_sync import get_cloud_sync
                        csync = get_cloud_sync()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "cloud_sync_stats", "data": csync.get_stats()})
                        elif action == "push":
                            result = csync.push(message.get("save_id", ""))
                            await manager.send_to_client(client_id, {"type": "cloud_sync_result", "data": result.to_dict()})
                        elif action == "sync":
                            result = csync.sync(message.get("save_id", ""))
                            await manager.send_to_client(client_id, {"type": "cloud_sync_result", "data": result.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "cloud_sync_error", "error": str(e)})

                elif msg_type == "rate_limiter":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_rate_limiter import get_rate_limiter
                        rl = get_rate_limiter()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "rate_limiter_stats", "data": rl.get_stats()})
                        elif action == "check":
                            allowed, detail = rl.allow(message.get("endpoint", "default"), message.get("request_id", ""), message.get("tokens", 1))
                            await manager.send_to_client(client_id, {"type": "rate_limiter_check", "data": {"allowed": allowed, "endpoint": message.get("endpoint", "")}})
                        elif action == "release":
                            rl.release(message.get("endpoint", "default"), message.get("request_id", ""))
                            await manager.send_to_client(client_id, {"type": "rate_limiter_released", "data": {"endpoint": message.get("endpoint", "")}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "rate_limiter_error", "error": str(e)})

                elif msg_type == "retry_system":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_retry_system import get_retry_system
                        rs = get_retry_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "retry_system_stats", "data": rs.get_stats()})
                        elif action == "circuit":
                            state = rs.get_circuit_state(message.get("operation", "default"))
                            await manager.send_to_client(client_id, {"type": "retry_circuit", "data": {"operation": message.get("operation", "default"), "state": state}})
                        elif action == "operations":
                            await manager.send_to_client(client_id, {"type": "retry_operations", "data": rs.list_operations()})
                        elif action == "reset":
                            rs.reset()
                            await manager.send_to_client(client_id, {"type": "retry_reset", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "retry_system_error", "error": str(e)})

                elif msg_type == "web_browser":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_web_browser import get_web_browser
                        wb = get_web_browser()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "web_browser_stats", "data": wb.get_stats()})
                        elif action == "fetch":
                            result = wb.fetch(message.get("url", ""), timeout=message.get("timeout"), bypass_cache=message.get("bypass_cache", False))
                            await manager.send_to_client(client_id, {"type": "web_browser_result", "data": result.to_dict()})
                        elif action == "fetch_text":
                            text = wb.fetch_text(message.get("url", ""), timeout=message.get("timeout"))
                            await manager.send_to_client(client_id, {"type": "web_browser_text", "data": {"url": message.get("url", ""), "text": text[:2000] if text else None}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "web_browser_error", "error": str(e)})

                elif msg_type == "session_search":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_session_search import get_session_search
                        ss = get_session_search()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "session_search_stats", "data": ss.get_stats()})
                        elif action == "search":
                            results = ss.quick_search(message.get("query", ""), message.get("limit", 10))
                            await manager.send_to_client(client_id, {"type": "session_search_results", "data": {"results": results}})
                        elif action == "index":
                            ss.index_session(message.get("session_id", ""), title=message.get("title", ""), messages=[message.get("content", "")], agent_id=message.get("agent_id", ""))
                            await manager.send_to_client(client_id, {"type": "session_search_indexed", "data": {"session_id": message.get("session_id", "")}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "session_search_error", "error": str(e)})

                elif msg_type == "object_pool":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.object_pool import get_object_pool_system
                        ops = get_object_pool_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "object_pool_stats", "data": ops.get_stats()})
                        elif action == "list":
                            await manager.send_to_client(client_id, {"type": "object_pool_list", "data": ops.list_pools()})
                        elif action == "shrink":
                            result = ops.shrink_all()
                            await manager.send_to_client(client_id, {"type": "object_pool_shrunk", "data": result})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "object_pool_error", "error": str(e)})

                elif msg_type == "lighting":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.lighting_system import get_lighting_system
                        ls = get_lighting_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "lighting_stats", "data": ls.get_stats()})
                        elif action == "lights":
                            lights = ls.list_lights()
                            await manager.send_to_client(client_id, {"type": "lighting_lights", "data": [l.to_dict() for l in lights]})
                        elif action == "create":
                            light = ls.create_light(
                                name=message.get("name", "Light"),
                                position=(message.get("x", 0.0), message.get("y", 0.0)),
                                intensity=message.get("intensity", 1.0),
                                radius=message.get("radius", 200.0),
                            )
                            await manager.send_to_client(client_id, {"type": "lighting_created", "data": light.to_dict()})
                        elif action == "position":
                            ls.set_light_position(message.get("light_id", ""), message.get("x", 0.0), message.get("y", 0.0))
                            await manager.send_to_client(client_id, {"type": "lighting_position", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "lighting_error", "error": str(e)})

                elif msg_type == "font":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.font_system import get_font_system, TextStyle
                        fs = get_font_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "font_stats", "data": fs.get_stats()})
                        elif action == "list":
                            fonts = fs.list_fonts()
                            await manager.send_to_client(client_id, {"type": "font_list", "data": [f.to_dict() for f in fonts]})
                        elif action == "measure":
                            font_id = message.get("font_id", "") or fs.get_default_font_id()
                            style = TextStyle(font_id=font_id, font_size=message.get("font_size", 16.0), max_width=message.get("max_width"))
                            block = fs.measure_text(message.get("text", ""), style)
                            await manager.send_to_client(client_id, {"type": "font_measured", "data": block.to_dict()})
                        elif action == "wrap":
                            font_id = message.get("font_id", "") or fs.get_default_font_id()
                            style = TextStyle(font_id=font_id, font_size=message.get("font_size", 16.0), max_width=message.get("max_width"))
                            lines = fs.wrap_text(message.get("text", ""), style)
                            await manager.send_to_client(client_id, {"type": "font_wrapped", "data": {"lines": lines}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "font_error", "error": str(e)})

                elif msg_type == "plugin":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.plugin_system import get_plugin_system
                        ps = get_plugin_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "plugin_stats", "data": ps.get_stats()})
                        elif action == "list":
                            await manager.send_to_client(client_id, {"type": "plugin_list", "data": ps.list_plugins()})
                        elif action == "active":
                            await manager.send_to_client(client_id, {"type": "plugin_active", "data": ps.list_active_plugins()})
                        elif action == "load":
                            success = ps.load_plugin(message.get("plugin_id", ""))
                            await manager.send_to_client(client_id, {"type": "plugin_loaded", "data": {"success": success, "plugin_id": message.get("plugin_id", "")}})
                        elif action == "activate":
                            success = ps.activate_plugin(message.get("plugin_id", ""))
                            await manager.send_to_client(client_id, {"type": "plugin_activated", "data": {"success": success}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "plugin_error", "error": str(e)})

                elif msg_type == "observability":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_observability import get_observability, LogLevel
                        obs = get_observability()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "observability_stats", "data": obs.get_stats()})
                        elif action == "metrics":
                            await manager.send_to_client(client_id, {"type": "observability_metrics", "data": obs.get_metric_snapshot()})
                        elif action == "traces":
                            traces = obs.get_recent_traces(message.get("limit", 50))
                            await manager.send_to_client(client_id, {"type": "observability_traces", "data": traces})
                        elif action == "logs":
                            level = None
                            if message.get("level"):
                                try:
                                    level = LogLevel[message.get("level").upper()]
                                except KeyError:
                                    pass
                            logs = obs.get_recent_logs(message.get("limit", 100), level)
                            await manager.send_to_client(client_id, {"type": "observability_logs", "data": [l.to_dict() for l in logs]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "observability_error", "error": str(e)})

                elif msg_type == "output_limiter":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_output_limiter import get_output_limiter
                        ol = get_output_limiter()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "output_limiter_stats", "data": ol.get_stats()})
                        elif action == "limit":
                            result = ol.limit(message.get("content", ""), message.get("content_type", "text"))
                            await manager.send_to_client(client_id, {"type": "output_limited", "data": result.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "output_limiter_error", "error": str(e)})

                elif msg_type == "context_engine":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_context_engine import get_context_engine, MessageRole, ContextStrategy
                        ce = get_context_engine()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "context_engine_stats", "data": ce.get_stats()})
                        elif action == "create_window":
                            try:
                                strat = ContextStrategy[message.get("strategy", "HYBRID")]
                            except KeyError:
                                strat = ContextStrategy.HYBRID
                            window = ce.create_window(
                                message.get("session_id", ""),
                                message.get("max_tokens", 8000),
                                strat,
                            )
                            await manager.send_to_client(client_id, {"type": "context_window_created", "data": window.to_dict()})
                        elif action == "add_message":
                            try:
                                role = MessageRole[message.get("role", "user").upper()]
                            except KeyError:
                                role = MessageRole.USER
                            msg = ce.add_message(
                                message.get("window_id", ""),
                                role,
                                message.get("content", ""),
                                message.get("importance", 0.5),
                            )
                            if msg:
                                await manager.send_to_client(client_id, {"type": "context_message_added", "data": msg.to_dict()})
                        elif action == "get_messages":
                            messages = ce.get_messages_for_llm(message.get("window_id", ""))
                            await manager.send_to_client(client_id, {"type": "context_messages", "data": {"messages": messages}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "context_engine_error", "error": str(e)})

                elif msg_type == "skill_discovery":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_skill_discovery import get_skill_discovery, CapabilityDomain
                        sd = get_skill_discovery()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "skill_discovery_stats", "data": sd.get_stats()})
                        elif action == "discover":
                            try:
                                dom = CapabilityDomain[message.get("domain").upper()] if message.get("domain") else None
                            except (KeyError, AttributeError):
                                dom = None
                            skills = sd.discover(message.get("query", ""), dom)
                            await manager.send_to_client(client_id, {"type": "skill_discovery_results", "data": {"skills": [s.to_dict() for s in skills]}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "skill_discovery_error", "error": str(e)})

                elif msg_type == "effects":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.effects_system import get_effects_system
                        es = get_effects_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "effects_stats", "data": es.get_stats()})
                        elif action == "stacks":
                            stacks = es.list_stacks()
                            await manager.send_to_client(client_id, {"type": "effects_stacks", "data": [s.to_dict() for s in stacks]})
                        elif action == "add":
                            instance = es.add_effect_by_preset(message.get("stack_id", ""), message.get("preset", "bloom_soft"))
                            await manager.send_to_client(client_id, {"type": "effects_added", "data": instance.to_dict() if instance else {}})
                        elif action == "toggle":
                            es.set_effect_enabled(message.get("stack_id", ""), message.get("instance_id", ""), message.get("enabled", True))
                            await manager.send_to_client(client_id, {"type": "effects_toggled", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "effects_error", "error": str(e)})

                elif msg_type == "input_mapping":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.input_mapping import get_input_mapping
                        im = get_input_mapping()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "input_mapping_stats", "data": im.get_stats()})
                        elif action == "contexts":
                            await manager.send_to_client(client_id, {"type": "input_mapping_contexts", "data": [c.to_dict() for c in im.list_contexts()]})
                        elif action == "bindings":
                            bindings = im.list_bindings(message.get("context_id"))
                            await manager.send_to_client(client_id, {"type": "input_mapping_bindings", "data": [b.to_dict() for b in bindings]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "input_mapping_error", "error": str(e)})

                elif msg_type == "undo_redo":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.undo_redo_system import get_undo_redo_system
                        ur = get_undo_redo_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "undo_redo_stats", "data": ur.get_stats()})
                        elif action == "undo":
                            cmd = ur.undo()
                            await manager.send_to_client(client_id, {"type": "undo_redo_undone", "data": {"command": cmd.to_dict() if cmd else None}})
                        elif action == "redo":
                            cmd = ur.redo()
                            await manager.send_to_client(client_id, {"type": "undo_redo_redone", "data": {"command": cmd.to_dict() if cmd else None}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "undo_redo_error", "error": str(e)})

                elif msg_type == "sprite_sheet":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.sprite_sheet import get_sprite_sheet_system
                        ss = get_sprite_sheet_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "sprite_sheet_stats", "data": ss.get_stats()})
                        elif action == "list":
                            sheets = ss.list_sheets()
                            await manager.send_to_client(client_id, {"type": "sprite_sheet_list", "data": [s.to_dict() for s in sheets]})
                        elif action == "play":
                            ss.play(message.get("entity_id", ""), message.get("sheet_id", ""), message.get("clip_name", ""), message.get("speed", 1.0))
                            await manager.send_to_client(client_id, {"type": "sprite_sheet_playing", "data": {"success": True}})
                        elif action == "pause":
                            ss.pause(message.get("entity_id", ""))
                            await manager.send_to_client(client_id, {"type": "sprite_sheet_paused", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "sprite_sheet_error", "error": str(e)})

                elif msg_type == "prompt_cache":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_prompt_cache import get_prompt_cache
                        pc = get_prompt_cache()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "prompt_cache_stats", "data": pc.get_stats()})
                        elif action == "hit_rate":
                            await manager.send_to_client(client_id, {"type": "prompt_cache_hit_rate", "data": pc.get_hit_rate()})
                        elif action == "clear":
                            pc.clear()
                            await manager.send_to_client(client_id, {"type": "prompt_cache_cleared", "data": {"success": True}})
                        elif action == "invalidate":
                            pc.invalidate(message.get("fingerprint", ""))
                            await manager.send_to_client(client_id, {"type": "prompt_cache_invalidated", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "prompt_cache_error", "error": str(e)})

                elif msg_type == "trajectory":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_trajectory_recorder import get_trajectory_recorder
                        tr = get_trajectory_recorder()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "trajectory_stats", "data": tr.get_stats()})
                        elif action == "sessions":
                            await manager.send_to_client(client_id, {"type": "trajectory_sessions", "data": tr.list_sessions()})
                        elif action == "export":
                            data = tr.export_session(message.get("session_id", ""))
                            await manager.send_to_client(client_id, {"type": "trajectory_exported", "data": data or {}})
                        elif action == "record":
                            evt = tr.record_event(message.get("event_type", "ENGINE_ACTION"), message.get("data", {}),
                                                  message.get("session_id", "default"))
                            await manager.broadcast_agent_event("trajectory_event", {"event_id": evt.event_id if evt else None})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "trajectory_error", "error": str(e)})

                elif msg_type == "checkpoint_sys":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_checkpoint_system import get_checkpoint_system
                        cs = get_checkpoint_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "checkpoint_sys_stats", "data": cs.get_stats()})
                        elif action == "chains":
                            await manager.send_to_client(client_id, {"type": "checkpoint_sys_chains", "data": cs.list_chains()})
                        elif action == "create":
                            cp = cs.create_checkpoint(message.get("chain_id", "default"), message.get("label", ""),
                                                       message.get("scope", "FULL"))
                            await manager.send_to_client(client_id, {"type": "checkpoint_sys_created",
                                "data": {"checkpoint_id": cp.checkpoint_id if cp else None}})
                        elif action == "rollback":
                            cp = cs.rollback(message.get("chain_id", "default"))
                            await manager.send_to_client(client_id, {"type": "checkpoint_sys_rolled_back",
                                "data": cp.to_dict() if cp else {"error": "Cannot rollback"}})
                        elif action == "restore":
                            success = cs.restore_checkpoint(message.get("chain_id", "default"), message.get("checkpoint_id", ""))
                            await manager.send_to_client(client_id, {"type": "checkpoint_sys_restored", "data": {"success": success}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "checkpoint_sys_error", "error": str(e)})

                elif msg_type == "budget_tracker":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_budget_tracker import get_budget_tracker
                        bt = get_budget_tracker()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "budget_tracker_stats", "data": bt.get_all_usage()})
                        elif action == "session":
                            await manager.send_to_client(client_id, {"type": "budget_tracker_session",
                                "data": bt.get_session_usage(message.get("session_id", "default"))})
                        elif action == "check":
                            can = bt.can_proceed(message.get("session_id", "default"), message.get("tokens", 0))
                            await manager.send_to_client(client_id, {"type": "budget_tracker_check", "data": {"can_proceed": can}})
                        elif action == "record":
                            alerts = bt.record_usage(message.get("session_id", "default"),
                                                     message.get("tokens_input", 0),
                                                     message.get("tokens_output", 0),
                                                     message.get("model", "default"))
                            await manager.broadcast_agent_event("budget_tracker_alerts",
                                {"alerts": {scope.value: level.value for scope, level in alerts.items()}})
                        elif action == "alerts":
                            await manager.send_to_client(client_id, {"type": "budget_tracker_alerts",
                                "data": [a.to_dict() for a in bt.get_recent_alerts()]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "budget_tracker_error", "error": str(e)})

                elif msg_type == "tween":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.tween_system import get_tween_system
                        ts = get_tween_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "tween_stats", "data": ts.get_stats()})
                        elif action == "list":
                            await manager.send_to_client(client_id, {"type": "tween_list", "data": ts.list_tweens()})
                        elif action == "create":
                            tid = ts.create(message.get("target_id", ""), message.get("property_name", "x"),
                                           message.get("start_value", 0.0), message.get("end_value", 0.0),
                                           message.get("duration", 1.0),
                                           message.get("easing", "LINEAR"),
                                           message.get("delay", 0.0),
                                           message.get("loop_mode", "ONCE"))
                            await manager.send_to_client(client_id, {"type": "tween_created", "data": {"tween_id": tid}})
                        elif action == "pause":
                            ts.pause(message.get("tween_id", ""))
                            await manager.send_to_client(client_id, {"type": "tween_paused", "data": {"success": True}})
                        elif action == "resume":
                            ts.resume(message.get("tween_id", ""))
                            await manager.send_to_client(client_id, {"type": "tween_resumed", "data": {"success": True}})
                        elif action == "cancel":
                            ts.cancel(message.get("tween_id", ""))
                            await manager.send_to_client(client_id, {"type": "tween_cancelled", "data": {"success": True}})
                        elif action == "create_group":
                            gid = ts.create_group(message.get("name", "group"), message.get("tween_ids", []),
                                                  message.get("mode", "parallel"))
                            await manager.send_to_client(client_id, {"type": "tween_group_created", "data": {"group_id": gid}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "tween_error", "error": str(e)})

                elif msg_type == "node_path":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.node_path_system import get_node_path_system
                        np = get_node_path_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "node_path_stats", "data": np.get_stats()})
                        elif action == "parse":
                            path = np.parse(message.get("path_str", ""))
                            await manager.send_to_client(client_id, {"type": "node_path_parsed",
                                "data": path.to_dict() if path else {"error": "Invalid path"}})
                        elif action == "resolve":
                            results = np.resolve(message.get("path_str", ""), message.get("root", {}))
                            await manager.send_to_client(client_id, {"type": "node_path_resolved", "data": {"results": results}})
                        elif action == "alias":
                            np.register_alias(message.get("name", ""), message.get("path_str", ""))
                            await manager.send_to_client(client_id, {"type": "node_path_alias_registered", "data": {"success": True}})
                        elif action == "aliases":
                            await manager.send_to_client(client_id, {"type": "node_path_aliases", "data": np.list_aliases()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "node_path_error", "error": str(e)})

                elif msg_type == "project_template":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.project_template import get_project_template_system
                        pts = get_project_template_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "project_template_stats", "data": pts.get_stats()})
                        elif action == "genres":
                            await manager.send_to_client(client_id, {"type": "project_template_genres", "data": pts.list_genres()})
                        elif action == "list":
                            templates = pts.list_by_genre(message.get("genre"))
                            await manager.send_to_client(client_id, {"type": "project_template_list",
                                "data": [t.to_dict() for t in (templates if templates else pts.list_all())]})
                        elif action == "get":
                            tmpl = pts.get(message.get("template_id", ""))
                            await manager.send_to_client(client_id, {"type": "project_template_detail",
                                "data": tmpl.to_dict() if tmpl else {"error": "Not found"}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "project_template_error", "error": str(e)})

                elif msg_type == "asset_pipeline":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.asset_pipeline import get_asset_pipeline
                        ap = get_asset_pipeline()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "asset_pipeline_stats", "data": ap.get_stats()})
                        elif action == "list":
                            await manager.send_to_client(client_id, {"type": "asset_pipeline_assets", "data": ap.list_assets()})
                        elif action == "categories":
                            await manager.send_to_client(client_id, {"type": "asset_pipeline_categories", "data": ap.list_categories()})
                        elif action == "search":
                            results = ap.search(message.get("query", ""))
                            await manager.send_to_client(client_id, {"type": "asset_pipeline_search",
                                "data": [r.to_dict() for r in results]})
                        elif action == "register":
                            aid = ap.register_asset(message.get("name", ""), message.get("category", ""),
                                                    message.get("format", ""), message.get("description", ""),
                                                    message.get("source_path", ""), message.get("tags", []))
                            await manager.send_to_client(client_id, {"type": "asset_pipeline_registered", "data": {"asset_id": aid}})
                        elif action == "bundle":
                            bid = ap.create_bundle(message.get("name", ""), message.get("asset_ids", []))
                            await manager.send_to_client(client_id, {"type": "asset_pipeline_bundled", "data": {"bundle_id": bid}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "asset_pipeline_error", "error": str(e)})

                elif msg_type == "insights":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_insights import get_insights_engine
                        ie = get_insights_engine()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "insights_stats", "data": ie.get_stats()})
                        elif action == "report":
                            report = ie.generate(days=message.get("days", 30))
                            await manager.send_to_client(client_id, {"type": "insights_report", "data": report.to_dict()})
                        elif action == "summary":
                            report = ie.generate(days=message.get("days", 7))
                            await manager.send_to_client(client_id, {"type": "insights_summary", "data": ie.format_summary(report)})
                        elif action == "track_task":
                            ie.track_task(message.get("started", False), message.get("completed", False),
                                         message.get("failed", False), message.get("iterations", 0))
                            await manager.send_to_client(client_id, {"type": "insights_task_tracked", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "insights_error", "error": str(e)})

                elif msg_type == "state_sync":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_state_sync import get_state_sync_mesh, SyncDomain
                        sm = get_state_sync_mesh()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "state_sync_stats", "data": sm.get_stats()})
                        elif action == "sync_all":
                            reports = sm.sync_all()
                            await manager.send_to_client(client_id, {"type": "state_sync_complete",
                                "data": {"domains_synced": len(reports)}})
                        elif action == "sync":
                            sd = SyncDomain[message.get("domain", "OBJECTS").upper()]
                            report = sm.sync_domain(sd)
                            await manager.send_to_client(client_id, {"type": "state_sync_domain_done",
                                "data": {"domain": report.domain.value, "conflicts": report.conflicts_found}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "state_sync_error", "error": str(e)})

                elif msg_type == "dev_loop":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_dev_loop import get_dev_loop
                        dl = get_dev_loop()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "dev_loop_stats", "data": dl.get_stats()})
                        elif action == "history":
                            await manager.send_to_client(client_id, {"type": "dev_loop_history",
                                "data": dl.get_history(message.get("limit", 20))})
                        elif action == "phase":
                            await manager.send_to_client(client_id, {"type": "dev_loop_phase",
                                "data": dl.get_phase().value})
                        elif action == "execute":
                            result = await dl.execute(message.get("task", ""))
                            await manager.broadcast_agent_event("dev_loop_result", {
                                "task_id": result.task_id, "success": result.success,
                                "iterations": result.total_iterations,
                            })
                        elif action == "abort":
                            dl.abort()
                            await manager.send_to_client(client_id, {"type": "dev_loop_aborted", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "dev_loop_error", "error": str(e)})

                elif msg_type == "context_refs":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.agent.agent_context_references import get_context_reference_resolver
                        cr = get_context_reference_resolver()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "context_refs_stats", "data": cr.get_stats()})
                        elif action == "parse":
                            refs = cr.parse_references(message.get("content", ""))
                            await manager.send_to_client(client_id, {"type": "context_refs_parsed",
                                "data": [{"domain": r.domain.value, "target": r.target} for r in refs]})
                        elif action == "resolve":
                            result = cr.resolve_message(message.get("content", ""),
                                                       message.get("max_tokens", 0))
                            await manager.send_to_client(client_id, {"type": "context_refs_resolved",
                                "data": {"found": result.found_count, "total": result.total_count}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "context_refs_error", "error": str(e)})

                elif msg_type == "rendering":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.rendering_server import get_rendering_server
                        rs = get_rendering_server()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "rendering_stats", "data": rs.get_stats()})
                        elif action == "commands":
                            cmds = rs.get_commands()
                            await manager.send_to_client(client_id, {"type": "rendering_commands",
                                "data": {"count": len(cmds), "frame": rs.get_stats().get("frames", 0)}})
                        elif action == "viewport":
                            rs.set_viewport(0, 0, message.get("width", 1920), message.get("height", 1080),
                                           message.get("scale", 1.0), message.get("cam_x", 0), message.get("cam_y", 0))
                            await manager.send_to_client(client_id, {"type": "rendering_viewport_set", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "rendering_error", "error": str(e)})

                elif msg_type == "input_events":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.input_event_system import get_input_event_system
                        ies = get_input_event_system()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "input_events_stats", "data": ies.get_stats()})
                        elif action == "emit_key":
                            evt = ies.emit_key(message.get("key_code", ""), message.get("pressed", True))
                            await manager.broadcast_agent_event("input_event", {"event_id": evt.event_id, "key": message.get("key_code")})
                        elif action == "emit_mouse":
                            evt = ies.emit_mouse(message.get("x", 0), message.get("y", 0),
                                                message.get("button", 0), message.get("pressed", False))
                            await manager.send_to_client(client_id, {"type": "input_event_emitted", "data": {"event_id": evt.event_id}})
                        elif action == "get_action":
                            val = ies.get_action_value(message.get("action_name", ""))
                            await manager.send_to_client(client_id, {"type": "input_action_value", "data": {"value": val}})
                        elif action == "flush":
                            flushed = ies.flush_events()
                            await manager.send_to_client(client_id, {"type": "input_events_flushed", "data": {"flushed": flushed}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "input_events_error", "error": str(e)})

                elif msg_type == "game_objects":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.game_object import get_game_object_registry, create_game_object
                        gor = get_game_object_registry()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "game_objects_stats", "data": gor.get_stats()})
                        elif action == "list":
                            objects = gor.find_by_tag(message.get("tag", "")) if message.get("tag") else gor.find_active()
                            await manager.send_to_client(client_id, {"type": "game_objects_list",
                                "data": [o.to_dict() for o in objects[:50]]})
                        elif action == "create":
                            go = create_game_object(message.get("name", "GameObject"),
                                                   (message.get("x", 0), message.get("y", 0)),
                                                   message.get("tags"))
                            await manager.broadcast_agent_event("game_object_created", go.to_dict())
                        elif action == "destroy_all":
                            count = gor.destroy_all()
                            await manager.send_to_client(client_id, {"type": "game_objects_destroyed", "data": {"count": count}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "game_objects_error", "error": str(e)})

                elif msg_type == "scene_manager":
                    action = message.get("action", "stats")
                    try:
                        from sparkai.engine.scene_manager import get_scene_manager
                        scm = get_scene_manager()
                        if action == "stats":
                            await manager.send_to_client(client_id, {"type": "scene_manager_stats", "data": scm.get_stats()})
                        elif action == "stack":
                            await manager.send_to_client(client_id, {"type": "scene_manager_stack",
                                "data": {"stack": scm.get_scene_stack(), "overlays": scm.get_overlay_stack()}})
                        elif action == "register":
                            defn = scm.register(message.get("name", ""), None, message.get("permanent", True),
                                              message.get("poolable", False), message.get("preload", False))
                            await manager.send_to_client(client_id, {"type": "scene_manager_registered",
                                "data": {"scene_id": defn.scene_id, "name": defn.name}})
                        elif action == "push":
                            inst = scm.push_scene(message.get("name", ""))
                            await manager.broadcast_agent_event("scene_pushed",
                                {"name": message.get("name", ""), "state": inst.state.value if inst else "error"})
                        elif action == "pop":
                            inst = scm.pop_scene()
                            await manager.broadcast_agent_event("scene_popped",
                                {"name": inst.definition.name if inst else "none"})
                        elif action == "active":
                            active = scm.get_active_scene()
                            await manager.send_to_client(client_id, {"type": "scene_manager_active",
                                "data": {"name": active.definition.name if active else "none"}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "scene_manager_error", "error": str(e)})

                elif msg_type == "process_registry":
                    try:
                        from sparkai.agent.agent_process_registry import get_process_registry
                        pr = get_process_registry()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "process_registry_stats", "data": pr.get_stats()})
                        elif sub == "list":
                            await manager.send_to_client(client_id, {"type": "process_registry_list", "data": [p.to_dict() for p in pr.list_all()]})
                        elif sub == "active":
                            await manager.send_to_client(client_id, {"type": "process_registry_active", "data": [p.to_dict() for p in pr.list_active()]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "process_registry_error", "error": str(e)})

                elif msg_type == "cron_scheduler":
                    try:
                        from sparkai.agent.agent_cron_scheduler import get_cron_scheduler
                        cs = get_cron_scheduler()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "cron_scheduler_stats", "data": cs.get_stats()})
                        elif sub == "jobs":
                            await manager.send_to_client(client_id, {"type": "cron_scheduler_jobs", "data": [
                                {"job_id": j.job_id, "name": j.name, "state": j.state.value} for j in cs._jobs.values()
                            ]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "cron_scheduler_error", "error": str(e)})

                elif msg_type == "expression_evaluator":
                    try:
                        from sparkai.agent.agent_expression_evaluator import get_expression_evaluator
                        ee = get_expression_evaluator()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "expression_evaluator_stats", "data": ee.get_stats()})
                        elif sub == "evaluate":
                            expr = data.get("expression", "")
                            result = ee.evaluate(expr)
                            await manager.send_to_client(client_id, {"type": "expression_evaluator_result", "data": {"expression": expr, "result": result}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "expression_evaluator_error", "error": str(e)})

                elif msg_type == "class_registry":
                    try:
                        from sparkai.agent.agent_class_registry import get_class_registry
                        cr = get_class_registry()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "class_registry_stats", "data": cr.get_stats()})
                        elif sub == "list":
                            await manager.send_to_client(client_id, {"type": "class_registry_types", "data": [t.to_dict() for t in cr.list_all()]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "class_registry_error", "error": str(e)})

                elif msg_type == "multi_modal":
                    try:
                        from sparkai.agent.agent_multi_modal import get_multi_modal_agent
                        mm = get_multi_modal_agent()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "multi_modal_stats", "data": mm.get_stats()})
                        elif sub == "reports":
                            await manager.send_to_client(client_id, {"type": "multi_modal_reports", "data": [r.to_dict() for r in mm.list_reports()]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "multi_modal_error", "error": str(e)})

                elif msg_type == "import_pipeline":
                    try:
                        from sparkai.agent.agent_import_pipeline import get_import_pipeline
                        ip = get_import_pipeline()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "import_pipeline_stats", "data": ip.get_stats()})
                        elif sub == "formats":
                            await manager.send_to_client(client_id, {"type": "import_pipeline_formats", "data": ip.list_supported_formats()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "import_pipeline_error", "error": str(e)})

                elif msg_type == "terrain_system":
                    try:
                        from sparkai.engine.terrain_system import get_terrain_system
                        ts = get_terrain_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "terrain_system_stats", "data": ts.get_stats()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "terrain_system_error", "error": str(e)})

                elif msg_type == "save_system":
                    try:
                        from sparkai.engine.save_system import get_save_system
                        ss = get_save_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "save_system_stats", "data": ss.get_stats()})
                        elif sub == "slots":
                            await manager.send_to_client(client_id, {"type": "save_system_slots", "data": [s.to_dict() for s in ss.list_slots()]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "save_system_error", "error": str(e)})

                elif msg_type == "network_sync":
                    try:
                        from sparkai.engine.network_sync import get_network_sync
                        ns = get_network_sync()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "network_sync_stats", "data": ns.get_stats()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "network_sync_error", "error": str(e)})

                elif msg_type == "behavior_tree":
                    try:
                        from sparkai.engine.behavior_tree import get_behavior_tree
                        bt = get_behavior_tree()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "behavior_tree_stats", "data": bt.get_stats()})
                        elif sub == "trees":
                            await manager.send_to_client(client_id, {"type": "behavior_tree_trees", "data": bt.list_trees()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "behavior_tree_error", "error": str(e)})

                elif msg_type == "math_utils":
                    try:
                        from sparkai.engine.math_utils import get_math_utils, Easing, Geometry2D, Interpolation, Vector2
                        mu = get_math_utils()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "math_utils_stats", "data": mu.get_stats()})
                        elif sub == "easing_curves":
                            await manager.send_to_client(client_id, {"type": "math_easing_curves", "data": Easing.list_all()})
                        elif sub == "easing":
                            curve = data.get("curve", "linear")
                            t = data.get("t", 0.5)
                            await manager.send_to_client(client_id, {"type": "math_easing", "data": {"curve": curve, "t": t, "value": Easing.apply(curve, t)}})
                        elif sub == "lerp":
                            result = Interpolation.lerp(data.get("a", 0.0), data.get("b", 1.0), data.get("t", 0.5))
                            await manager.send_to_client(client_id, {"type": "math_lerp", "data": {"result": result}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "math_utils_error", "error": str(e)})

                elif msg_type == "gui_system":
                    try:
                        from sparkai.engine.gui_system import get_gui_system
                        gs = get_gui_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "gui_system_stats", "data": gs.get_stats()})
                        elif sub == "root":
                            root = gs.root
                            await manager.send_to_client(client_id, {"type": "gui_system_root", "data": root.to_dict() if root else None})
                        elif sub == "create_root":
                            gs.create_root(data.get("width", 800), data.get("height", 600))
                            await manager.send_to_client(client_id, {"type": "gui_system_created", "data": gs.root.to_dict() if gs.root else None})
                        elif sub == "mouse_click":
                            widget_id = gs.handle_mouse_click(data.get("x", 0.0), data.get("y", 0.0))
                            await manager.send_to_client(client_id, {"type": "gui_mouse_click", "data": {"widget": widget_id}})
                        elif sub == "themes":
                            await manager.send_to_client(client_id, {"type": "gui_themes", "data": {"active": gs._active_theme, "themes": list(gs._themes.keys())}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "gui_system_error", "error": str(e)})

                elif msg_type == "config_manager":
                    try:
                        from sparkai.engine.config_manager import get_config_manager
                        cm = get_config_manager()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "config_manager_stats", "data": cm.get_stats()})
                        elif sub == "get":
                            key = data.get("key", "")
                            await manager.send_to_client(client_id, {"type": "config_manager_value", "data": {"key": key, "value": cm.get(key)}})
                        elif sub == "keys":
                            await manager.send_to_client(client_id, {"type": "config_manager_keys", "data": cm.list_keys()})
                        elif sub == "all":
                            await manager.send_to_client(client_id, {"type": "config_manager_all", "data": cm.get_all()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "config_manager_error", "error": str(e)})

                elif msg_type == "animation_controller":
                    try:
                        from sparkai.engine.animation_controller import get_animation_controller
                        ac = get_animation_controller()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "animation_controller_stats", "data": ac.get_stats()})
                        elif sub == "active_states":
                            await manager.send_to_client(client_id, {"type": "animation_active_states", "data": ac.get_active_state_names()})
                        elif sub == "clips":
                            clips = [c.to_dict() for c in ac._clip_library.values()]
                            await manager.send_to_client(client_id, {"type": "animation_clips", "data": clips})
                        elif sub == "parameters":
                            params = [p.to_dict() for p in ac._parameters.values()]
                            await manager.send_to_client(client_id, {"type": "animation_parameters", "data": params})
                        elif sub == "update":
                            ac.update(data.get("delta_time", 0.016))
                            await manager.send_to_client(client_id, {"type": "animation_updated", "data": ac.get_stats()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "animation_controller_error", "error": str(e)})

                elif msg_type == "trajectory_v2":
                    try:
                        from sparkai.agent.agent_trajectory import get_trajectory_recorder, TrajectoryPhase
                        tr = get_trajectory_recorder()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "trajectory_v2_stats", "data": tr.get_stats()})
                        elif sub == "sessions":
                            sessions = [s.to_dict() for s in tr._sessions.values()]
                            await manager.send_to_client(client_id, {"type": "trajectory_v2_sessions", "data": sessions})
                        elif sub == "start":
                            session = tr.start_session(data.get("session_id", ""), data.get("project_name", ""))
                            await manager.send_to_client(client_id, {"type": "trajectory_v2_started", "data": session.to_dict()})
                        elif sub == "end":
                            session = tr.end_session(data.get("session_id", ""), data.get("outcome", "success"))
                            await manager.send_to_client(client_id, {"type": "trajectory_v2_ended", "data": session.to_dict() if session else None})
                        elif sub == "replay":
                            summary = tr.replay_summary(data.get("session_id", ""))
                            await manager.send_to_client(client_id, {"type": "trajectory_v2_replay", "data": summary})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "trajectory_v2_error", "error": str(e)})

                elif msg_type == "skill_commands":
                    try:
                        from sparkai.agent.agent_skill_commands import get_skill_command_registry
                        scr = get_skill_command_registry()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "skill_commands_stats", "data": scr.get_stats()})
                        elif sub == "list":
                            cmds = [c.to_dict() for c in scr.list_commands()]
                            await manager.send_to_client(client_id, {"type": "skill_commands_list", "data": cmds})
                        elif sub == "help":
                            cmd_name = data.get("command", "")
                            help_text = scr.get_help(cmd_name)
                            await manager.send_to_client(client_id, {"type": "skill_commands_help", "data": {"command": cmd_name, "help": help_text}})
                        elif sub == "execute":
                            result = scr.execute(data.get("command", ""), data.get("args", {}), data.get("user_id", "ws"))
                            await manager.send_to_client(client_id, {"type": "skill_commands_result", "data": result.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "skill_commands_error", "error": str(e)})

                elif msg_type == "session_store":
                    try:
                        from sparkai.agent.agent_session_persistence import get_session_store
                        ss = get_session_store()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "session_store_stats", "data": ss.get_stats()})
                        elif sub == "search":
                            results = ss.search(
                                query=data.get("query", ""),
                                tag=data.get("tag", ""),
                                project_name=data.get("project_name", ""),
                                limit=data.get("limit", 20),
                            )
                            await manager.send_to_client(client_id, {"type": "session_store_search", "data": [r.to_dict() for r in results]})
                        elif sub == "active":
                            active = [r.to_dict() for r in ss.find_active()]
                            await manager.send_to_client(client_id, {"type": "session_store_active", "data": active})
                        elif sub == "create":
                            record = ss.create(
                                data.get("title", "WS Session"),
                                data.get("project_name", ""),
                                data.get("tags", []),
                            )
                            await manager.send_to_client(client_id, {"type": "session_store_created", "data": record.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "session_store_error", "error": str(e)})

                elif msg_type == "platform_bridge":
                    try:
                        from sparkai.agent.agent_platform_bridge import get_platform_bridge, PlatformType, MessageRole, MessageFormat
                        pb = get_platform_bridge()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "platform_bridge_stats", "data": pb.get_stats()})
                        elif sub == "platforms":
                            configs = pb.list_platforms()
                            await manager.send_to_client(client_id, {"type": "platform_bridge_platforms", "data": {k.value: v for k, v in configs.items()}})
                        elif sub == "send":
                            platform = PlatformType(data.get("platform", "web"))
                            role = MessageRole(data.get("role", "assistant"))
                            fmt = MessageFormat(data.get("format", "markdown"))
                            msg = pb.send(platform, role, data.get("content", ""), fmt)
                            await manager.send_to_client(client_id, {"type": "platform_bridge_sent", "data": msg.to_dict()})
                        elif sub == "broadcast":
                            msgs = pb.send_to_all(MessageRole.SYSTEM, data.get("content", ""))
                            await manager.send_to_client(client_id, {"type": "platform_bridge_broadcast", "data": {"count": len(msgs)}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "platform_bridge_error", "error": str(e)})

                elif msg_type == "reasoning_chain":
                    try:
                        from sparkai.agent.agent_reasoning_chain import get_reasoning_chain, ReasoningPhase
                        rc = get_reasoning_chain()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "reasoning_chain_stats", "data": rc.get_stats()})
                        elif sub == "begin":
                            trace = rc.begin(data.get("goal", ""))
                            await manager.send_to_client(client_id, {"type": "reasoning_chain_trace", "data": trace.to_dict()})
                        elif sub == "think":
                            step = rc.think(data.get("thought", ""), ReasoningPhase(data.get("phase", "analyze")))
                            await manager.send_to_client(client_id, {"type": "reasoning_chain_step", "data": step.to_dict() if step else None})
                        elif sub == "finish":
                            trace = rc.finish(data.get("outcome", ""), data.get("success", True))
                            await manager.send_to_client(client_id, {"type": "reasoning_chain_finished", "data": trace.to_dict() if trace else None})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "reasoning_chain_error", "error": str(e)})

                elif msg_type == "tool_composer":
                    try:
                        from sparkai.agent.agent_tool_composer import get_tool_composer
                        tc = get_tool_composer()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "tool_composer_stats", "data": tc.get_stats()})
                        elif sub == "create_chain":
                            chain = tc.create_chain(data.get("name", "chain"))
                            await manager.send_to_client(client_id, {"type": "tool_chain_created", "data": chain.to_dict()})
                        elif sub == "templates":
                            templates = [t.to_dict() for t in tc.list_templates()]
                            await manager.send_to_client(client_id, {"type": "tool_templates", "data": templates})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "tool_composer_error", "error": str(e)})

                elif msg_type == "feedback_loop":
                    try:
                        from sparkai.agent.agent_feedback_loop import get_feedback_loop
                        fl = get_feedback_loop()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "feedback_loop_stats", "data": fl.get_stats()})
                        elif sub == "report":
                            await manager.send_to_client(client_id, {"type": "feedback_report", "data": fl.get_quality_report()})
                        elif sub == "record":
                            entry = fl.record(data.get("action_type", ""), "user", data.get("sentiment", "neutral"), data.get("score", 0.5), data.get("message", ""))
                            await manager.send_to_client(client_id, {"type": "feedback_recorded", "data": entry.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "feedback_loop_error", "error": str(e)})

                elif msg_type == "agent_negotiation":
                    try:
                        from sparkai.agent.agent_negotiation import get_agent_negotiation
                        an = get_agent_negotiation()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "negotiation_stats", "data": an.get_stats()})
                        elif sub == "open":
                            session = an.open_session(data.get("topic", ""), data.get("description", ""))
                            await manager.send_to_client(client_id, {"type": "negotiation_opened", "data": session.to_dict()})
                        elif sub == "resolve":
                            result = an.resolve_session(data.get("session_id", ""))
                            await manager.send_to_client(client_id, {"type": "negotiation_resolved", "data": result.to_dict() if result else None})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "negotiation_error", "error": str(e)})

                elif msg_type == "debug_draw":
                    try:
                        from sparkai.engine.debug_draw_system import get_debug_draw_system, DrawCategory
                        dd = get_debug_draw_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "debug_draw_stats", "data": dd.get_stats()})
                        elif sub == "toggle":
                            dd.enabled = data.get("enabled", True)
                            await manager.send_to_client(client_id, {"type": "debug_draw_toggled", "data": {"enabled": dd.enabled}})
                        elif sub == "clear":
                            dd.clear()
                            await manager.send_to_client(client_id, {"type": "debug_draw_cleared", "data": {}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "debug_draw_error", "error": str(e)})

                elif msg_type == "prefab_system":
                    try:
                        from sparkai.engine.prefab_system import get_prefab_system
                        ps = get_prefab_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "prefab_stats", "data": ps.get_stats()})
                        elif sub == "templates":
                            templates = [t.to_dict() for t in ps.list_templates()]
                            await manager.send_to_client(client_id, {"type": "prefab_templates", "data": templates})
                        elif sub == "instantiate":
                            inst = ps.instantiate(data.get("template_id", ""), data.get("x", 0.0), data.get("y", 0.0))
                            await manager.send_to_client(client_id, {"type": "prefab_instantiated", "data": inst.to_dict() if inst else None})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "prefab_system_error", "error": str(e)})

                elif msg_type == "physics_constraints":
                    try:
                        from sparkai.engine.physics_constraints import get_physics_constraints
                        pc = get_physics_constraints()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "physics_constraints_stats", "data": pc.get_stats()})
                        elif sub == "create_spring":
                            c = pc.create_spring(data.get("body_a", ""), data.get("body_b", ""), data.get("rest_length", 50.0))
                            await manager.send_to_client(client_id, {"type": "constraint_created", "data": c.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "physics_constraints_error", "error": str(e)})

                elif msg_type == "spatial_index":
                    try:
                        from sparkai.engine.spatial_index import get_spatial_index
                        si = get_spatial_index()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "spatial_index_stats", "data": si.get_stats()})
                        elif sub == "query_range":
                            results = si.query_range(data.get("x", 0), data.get("y", 0), data.get("w", 500), data.get("h", 500))
                            await manager.send_to_client(client_id, {"type": "spatial_query_results", "data": [r.to_dict() for r in results]})
                        elif sub == "insert":
                            entry = si.insert(data.get("id", ""), data.get("x", 0), data.get("y", 0), data.get("w", 0), data.get("h", 0))
                            await manager.send_to_client(client_id, {"type": "spatial_entry_inserted", "data": entry.to_dict() if entry else None})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "spatial_index_error", "error": str(e)})

                elif msg_type == "simulation_env":
                    try:
                        from sparkai.agent.agent_simulation_env import get_simulation_env
                        se = get_simulation_env()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "simulation_stats", "data": se.get_stats()})
                        elif sub == "create_scenario":
                            scenario = se.create_scenario(data.get("name", "untitled"), data.get("description", ""))
                            await manager.send_to_client(client_id, {"type": "scenario_created", "data": scenario.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "simulation_error", "error": str(e)})

                elif msg_type == "goal_decomposer":
                    try:
                        from sparkai.agent.agent_goal_decomposer import get_goal_decomposer
                        gd = get_goal_decomposer()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "goal_decomposer_stats", "data": gd.get_stats()})
                        elif sub == "create_tree":
                            tree = gd.create_goal_tree(data.get("root_title", "Untitled"), data.get("root_description", ""))
                            await manager.send_to_client(client_id, {"type": "goal_tree_created", "data": tree.to_full_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "goal_decomposer_error", "error": str(e)})

                elif msg_type == "prompt_template":
                    try:
                        from sparkai.agent.agent_prompt_template import get_prompt_template_lib
                        ptl = get_prompt_template_lib()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "prompt_template_stats", "data": ptl.get_stats()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "prompt_template_error", "error": str(e)})

                elif msg_type == "semantic_memory":
                    try:
                        from sparkai.agent.agent_semantic_memory import get_semantic_memory
                        sm = get_semantic_memory()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "semantic_memory_stats", "data": sm.get_stats()})
                        elif sub == "store":
                            memory = sm.store(data.get("content", ""), tags=data.get("tags", "").split(",") if data.get("tags") else None)
                            await manager.send_to_client(client_id, {"type": "memory_stored", "data": memory.to_full_dict()})
                        elif sub == "search":
                            results = sm.search(data.get("query", ""), top_k=data.get("top_k", 10))
                            await manager.send_to_client(client_id, {"type": "search_results", "data": [{"memory": m.to_full_dict(), "score": round(s, 4)} for m, s in results]})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "semantic_memory_error", "error": str(e)})

                elif msg_type == "procedural_generation":
                    try:
                        from sparkai.engine.procedural_generation import get_procedural_generator
                        pg = get_procedural_generator()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "procedural_stats", "data": pg.get_stats()})
                        elif sub == "generate_terrain":
                            terrain = pg.generate_terrain(seed=data.get("seed", 42))
                            await manager.send_to_client(client_id, {"type": "terrain_generated", "data": terrain.to_dict()})
                        elif sub == "generate_dungeon":
                            dungeon = pg.generate_dungeon(seed=data.get("seed", 42))
                            await manager.send_to_client(client_id, {"type": "dungeon_generated", "data": dungeon.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "procedural_error", "error": str(e)})

                elif msg_type == "ragdoll_physics":
                    try:
                        from sparkai.engine.ragdoll_physics import get_ragdoll_system
                        rs = get_ragdoll_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "ragdoll_stats", "data": rs.get_stats()})
                        elif sub == "create_humanoid":
                            skeleton = rs.build_humanoid(data.get("name", "humanoid"))
                            await manager.send_to_client(client_id, {"type": "ragdoll_created", "data": skeleton.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "ragdoll_error", "error": str(e)})

                elif msg_type == "telemetry":
                    try:
                        from sparkai.engine.game_telemetry import get_telemetry_engine
                        te = get_telemetry_engine()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "telemetry_stats", "data": te.get_stats()})
                        elif sub == "start_session":
                            session = te.start_session(data.get("player_id", ""))
                            await manager.send_to_client(client_id, {"type": "session_started", "data": session.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "telemetry_error", "error": str(e)})

                elif msg_type == "network_rpc":
                    try:
                        from sparkai.engine.network_rpc import get_network_rpc
                        nrpc = get_network_rpc()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "network_rpc_stats", "data": nrpc.get_stats()})
                        elif sub == "register_handler":
                            nrpc.register_handler(data.get("procedure", ""), lambda p: {"received": True})
                            await manager.send_to_client(client_id, {"type": "handler_registered", "data": {"procedure": data.get("procedure", "")}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "network_rpc_error", "error": str(e)})

                elif msg_type == "intent_classifier":
                    try:
                        from sparkai.agent.agent_intent_classifier import get_intent_classifier
                        ic = get_intent_classifier()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "intent_classifier_stats", "data": ic.get_stats()})
                        elif sub == "classify":
                            result = ic.classify(data.get("query", ""))
                            await manager.send_to_client(client_id, {"type": "intent_result", "data": result.to_dict()})
                        elif sub == "route":
                            target = ic.get_routing_target(data.get("query", ""))
                            await manager.send_to_client(client_id, {"type": "routing_target", "data": target})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "intent_classifier_error", "error": str(e)})

                elif msg_type == "context_assembler":
                    try:
                        from sparkai.agent.agent_context_assembler import get_context_assembler
                        ca = get_context_assembler()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "context_assembler_stats", "data": ca.get_stats()})
                        elif sub == "assemble":
                            ctx = ca.assemble(include_recent_history=data.get("history", 10))
                            await manager.send_to_client(client_id, {"type": "assembled_context", "data": ctx.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "context_assembler_error", "error": str(e)})

                elif msg_type == "action_sequencer":
                    try:
                        from sparkai.agent.agent_action_sequencer import get_action_sequencer
                        aseq = get_action_sequencer()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "action_sequencer_stats", "data": aseq.get_stats()})
                        elif sub == "create_pipeline":
                            pipeline = aseq.create_pipeline(data.get("name", ""))
                            await manager.send_to_client(client_id, {"type": "pipeline_created", "data": pipeline.to_full_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "action_sequencer_error", "error": str(e)})

                elif msg_type == "console_system":
                    try:
                        from sparkai.engine.console_system import get_console_system
                        cs = get_console_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "console_stats", "data": cs.get_stats()})
                        elif sub == "execute":
                            result = cs.execute(data.get("command", ""))
                            await manager.send_to_client(client_id, {"type": "console_result", "data": {"result": result}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "console_error", "error": str(e)})

                elif msg_type == "input_recorder":
                    try:
                        from sparkai.engine.input_recorder import get_input_recorder
                        ir = get_input_recorder()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "input_recorder_stats", "data": ir.get_stats()})
                        elif sub == "start_recording":
                            session = ir.start_recording(data.get("name", ""))
                            await manager.send_to_client(client_id, {"type": "recording_started", "data": session.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "input_recorder_error", "error": str(e)})

                elif msg_type == "collision_layers":
                    try:
                        from sparkai.engine.collision_layers import get_collision_layer_manager
                        clm = get_collision_layer_manager()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "collision_layers_stats", "data": clm.get_stats()})
                        elif sub == "check":
                            should = clm.check_collision(data.get("mask_a", 0), data.get("mask_b", 0))
                            await manager.send_to_client(client_id, {"type": "collision_check", "data": {"should_collide": should}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "collision_layers_error", "error": str(e)})

                elif msg_type == "camera_shake":
                    try:
                        from sparkai.engine.camera_shake import get_camera_shake_system
                        cs = get_camera_shake_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "camera_shake_stats", "data": cs.get_stats()})
                        elif sub == "state":
                            await manager.send_to_client(client_id, {"type": "camera_shake_state", "data": cs.get_state()})
                        elif sub == "shake":
                            from sparkai.engine.camera_shake import ShakePreset, ShakeConfig
                            preset = data.get("preset", "impact")
                            try:
                                pe = ShakePreset[preset.upper()]
                            except KeyError:
                                pe = ShakePreset.IMPACT
                            intensity = data.get("intensity", 1.0)
                            config = ShakeConfig(
                                amplitude_x=10.0 * intensity,
                                amplitude_y=10.0 * intensity,
                                frequency=30.0,
                                duration=data.get("duration", 0.5),
                                decay=0.9,
                            )
                            cs.shake(preset=pe, config=config)
                            await manager.send_to_client(client_id, {"type": "camera_shake_triggered", "data": {"preset": preset}})
                        elif sub == "follow":
                            cs.set_target(data.get("target_x", 0.0), data.get("target_y", 0.0))
                            cs.set_follow_speed(data.get("speed", 5.0))
                            await manager.send_to_client(client_id, {"type": "camera_follow_set", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "camera_shake_error", "error": str(e)})

                elif msg_type == "difficulty_system":
                    try:
                        from sparkai.engine.difficulty_system import get_difficulty_system, DifficultyTier
                        ds = get_difficulty_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "difficulty_stats", "data": ds.get_stats()})
                        elif sub == "set_tier":
                            tier_name = data.get("tier", "normal")
                            try:
                                tier = DifficultyTier(tier_name.upper())
                            except ValueError:
                                tier = DifficultyTier.NORMAL
                            ds.set_tier(tier)
                            ds.set_level(data.get("level", 1))
                            await manager.send_to_client(client_id, {"type": "difficulty_updated", "data": {"tier": tier_name, "level": data.get("level", 1)}})
                        elif sub == "get_params":
                            await manager.send_to_client(client_id, {"type": "difficulty_params", "data": ds.get_current_params()})
                        elif sub == "record_death":
                            ds.record_death()
                            await manager.send_to_client(client_id, {"type": "difficulty_event_recorded", "data": {"event": "death"}})
                        elif sub == "record_complete":
                            ds.record_level_complete()
                            await manager.send_to_client(client_id, {"type": "difficulty_event_recorded", "data": {"event": "complete"}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "difficulty_system_error", "error": str(e)})

                elif msg_type == "fog_of_war":
                    try:
                        from sparkai.engine.fog_of_war import get_fog_of_war, FogShape
                        fow = get_fog_of_war()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "fog_of_war_stats", "data": fow.get_stats()})
                        elif sub == "check_visible":
                            tile_size = fow._tile_size if hasattr(fow, '_tile_size') else 32.0
                            tx = int(data.get("x", 0.0) / tile_size)
                            ty = int(data.get("y", 0.0) / tile_size)
                            visible = fow.is_visible(tx, ty, data.get("team_id", 0))
                            await manager.send_to_client(client_id, {"type": "fog_visibility", "data": {"visible": visible}})
                        elif sub == "exploration":
                            pct = fow.get_exploration_percentage(data.get("team_id", 0))
                            await manager.send_to_client(client_id, {"type": "fog_exploration", "data": {"percentage": pct}})
                        elif sub == "add_vision":
                            shape_str = data.get("shape", "circle")
                            try:
                                shape = FogShape[shape_str.upper()]
                            except KeyError:
                                shape = FogShape.CIRCLE
                            fow.add_vision_source(
                                source_id=data.get("source_id", ""),
                                team=data.get("team_id", 0),
                                x=data.get("x", 0.0), y=data.get("y", 0.0),
                                radius=data.get("radius", 5.0),
                                shape=shape,
                                cone_angle=data.get("cone_angle", 360.0),
                                cone_direction=data.get("cone_direction", 0.0),
                            )
                            await manager.send_to_client(client_id, {"type": "fog_vision_added", "data": {"source_id": data.get("source_id", "")}})
                        elif sub == "remove_vision":
                            fow.remove_vision_source(data.get("source_id", ""))
                            await manager.send_to_client(client_id, {"type": "fog_vision_removed", "data": {"source_id": data.get("source_id", "")}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "fog_of_war_error", "error": str(e)})

                elif msg_type == "game_modes":
                    try:
                        from sparkai.engine.game_modes import get_game_mode_system
                        gm = get_game_mode_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "game_modes_stats", "data": gm.get_stats()})
                        elif sub == "current":
                            await manager.send_to_client(client_id, {"type": "game_modes_current", "data": {"mode": gm.get_current()}})
                        elif sub == "stack":
                            await manager.send_to_client(client_id, {"type": "game_modes_stack", "data": {"stack": gm.get_stack_names(), "count": len(gm.get_mode_stack())}})
                        elif sub == "push":
                            success = gm.push(data.get("mode_name", ""), **data.get("params", {}))
                            await manager.send_to_client(client_id, {"type": "game_modes_pushed", "data": {"success": success, "mode": data.get("mode_name", "")}})
                        elif sub == "pop":
                            popped = gm.pop()
                            await manager.send_to_client(client_id, {"type": "game_modes_popped", "data": {"success": popped is not None, "popped_mode": popped}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "game_modes_error", "error": str(e)})

                elif msg_type == "agent_event_bus":
                    try:
                        from sparkai.agent.agent_event_bus import get_agent_event_bus, EventDomain, EventPriority, AgentEvent
                        eb = get_agent_event_bus()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "event_bus_stats", "data": eb.get_stats()})
                        elif sub == "emit":
                            domain_str = data.get("domain", "custom")
                            try:
                                domain = EventDomain(domain_str)
                            except ValueError:
                                domain = EventDomain.CUSTOM
                            priority_str = data.get("priority", "normal")
                            try:
                                priority = EventPriority[priority_str.upper()]
                            except KeyError:
                                priority = EventPriority.NORMAL
                            event = eb.emit(
                                domain=domain,
                                event_type=data.get("name", ""),
                                data=data.get("data", {}),
                                source=data.get("source", "ws"),
                                priority=priority,
                            )
                            await manager.send_to_client(client_id, {"type": "event_emitted", "data": {"event_id": event.event_id, "event_name": data.get("name", "")}})
                        elif sub == "history":
                            domain_raw = data.get("domain")
                            domain_filter = None
                            if domain_raw:
                                try:
                                    domain_filter = EventDomain(domain_raw)
                                except ValueError:
                                    domain_filter = EventDomain.CUSTOM
                            history = eb.get_history(limit=data.get("limit", 50), domain=domain_filter)
                            await manager.send_to_client(client_id, {"type": "event_bus_history", "data": {"history": [e.to_dict() for e in history]}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "event_bus_error", "error": str(e)})

                elif msg_type == "agent_task_queue":
                    try:
                        from sparkai.agent.agent_task_queue import get_agent_task_queue, TaskPriority, TaskCategory
                        tq = get_agent_task_queue()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "task_queue_stats", "data": tq.get_stats()})
                        elif sub == "list":
                            tasks = tq.list_tasks(state=data.get("status"))
                            await manager.send_to_client(client_id, {"type": "task_queue_list", "data": {"tasks": tasks, "count": len(tasks)}})
                        elif sub == "submit":
                            priority_str = data.get("priority", "normal")
                            try:
                                pri = TaskPriority(priority_str)
                            except ValueError:
                                pri = TaskPriority.NORMAL
                            cat_str = data.get("category", "general")
                            try:
                                cat = TaskCategory(cat_str)
                            except ValueError:
                                cat = TaskCategory.CUSTOM
                            task_id = tq.submit(
                                name=data.get("name", ""),
                                handler=lambda payload: {"status": "completed", "payload": payload},
                                priority=pri,
                                category=cat,
                                payload=data.get("payload", {}),
                                dependencies=data.get("dependencies", []),
                            )
                            await manager.send_to_client(client_id, {"type": "task_submitted", "data": {"task_id": task_id}})
                        elif sub == "cancel":
                            success = tq.cancel(data.get("task_id", ""))
                            await manager.send_to_client(client_id, {"type": "task_cancelled", "data": {"success": success}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "task_queue_error", "error": str(e)})

                elif msg_type == "code_review":
                    try:
                        from sparkai.agent.agent_code_review import get_code_review_engine
                        cr = get_code_review_engine()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "code_review_stats", "data": cr.get_stats()})
                        elif sub == "review":
                            report = cr.review(file_path="<ws>", code=data.get("code", ""))
                            await manager.send_to_client(client_id, {"type": "code_review_result", "data": report.to_dict()})
                        elif sub == "batch_review":
                            files_dict = {f.get("file_path", f"<ws_{i}>"): f.get("code", "") for i, f in enumerate(data.get("files", []))}
                            report = cr.review_multiple(files_dict)
                            await manager.send_to_client(client_id, {"type": "code_review_batch", "data": report.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "code_review_error", "error": str(e)})

                elif msg_type == "agent_pipeline":
                    try:
                        from sparkai.agent.agent_pipeline import get_agent_pipeline
                        ap = get_agent_pipeline()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "agent_pipeline_stats", "data": ap.get_stats()})
                        elif sub == "list_runs":
                            runs = ap.list_runs(limit=data.get("limit", 20))
                            await manager.send_to_client(client_id, {"type": "agent_pipeline_runs", "data": {"runs": runs}})
                        elif sub == "execute":
                            run = await ap.execute(
                                inputs=data.get("inputs", {}),
                                definition_name=data.get("definition_name", ""),
                            )
                            await manager.send_to_client(client_id, {"type": "agent_pipeline_executing", "data": run.to_dict()})
                        elif sub == "cancel":
                            success = ap.cancel_run(data.get("run_id", ""))
                            await manager.send_to_client(client_id, {"type": "agent_pipeline_cancelled", "data": {"success": success}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "agent_pipeline_error", "error": str(e)})

                elif msg_type == "agent_consensus":
                    try:
                        from sparkai.agent.agent_consensus import get_agent_consensus, ConsensusProtocol
                        ac = get_agent_consensus()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "consensus_stats", "data": ac.get_stats()})
                        elif sub == "propose":
                            try:
                                protocol = ConsensusProtocol(data.get("protocol", "majority"))
                            except ValueError:
                                protocol = ConsensusProtocol.MAJORITY
                            result = ac.propose(
                                topic=data.get("topic", ""),
                                description=data.get("description", ""),
                                context=data.get("context", {}),
                                protocol=protocol,
                                min_participants=data.get("min_participants", 2),
                            )
                            await manager.broadcast_agent_event("consensus_proposed", {"round_id": result.round_id, "topic": data.get("topic", "")})
                        elif sub == "submit_opinion":
                            opinion = ac.submit_opinion(
                                round_id=data.get("round_id", ""),
                                agent_name=data.get("agent_name", ""),
                                position=data.get("position", ""),
                                reasoning=data.get("reasoning", ""),
                                confidence=data.get("confidence", 0.5),
                            )
                            await manager.broadcast_agent_event("opinion_submitted", {"opinion_id": opinion.opinion_id})
                        elif sub == "vote":
                            ac.vote(round_id=data.get("round_id", ""), agent_name=data.get("agent_name", ""), position=data.get("position", ""), weight=data.get("weight", 1.0))
                            await manager.broadcast_agent_event("vote_cast", {"round_id": data.get("round_id", "")})
                        elif sub == "resolve":
                            result = ac.resolve(data.get("round_id", ""))
                            await manager.broadcast_agent_event("consensus_resolved", {"winning_position": result.winning_position, "confidence": result.confidence})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "consensus_error", "error": str(e)})

                elif msg_type == "game_analyzer":
                    try:
                        from sparkai.agent.agent_game_analyzer import get_game_analyzer, AnalysisDimension
                        ga = get_game_analyzer()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "game_analyzer_stats", "data": ga.get_stats()})
                        elif sub == "analyze":
                            dims = None
                            if data.get("target_dimensions"):
                                try:
                                    dims = [AnalysisDimension(d) for d in data.get("target_dimensions", [])]
                                except ValueError:
                                    pass
                            report = ga.analyze(
                                design_doc=data.get("game_design_doc", ""),
                                rules=data.get("rules"),
                                mechanics=data.get("mechanics"),
                                target_dimensions=dims,
                            )
                            await manager.broadcast_agent_event("game_analysis_complete", report.to_dict())
                        elif sub == "reports":
                            reports = ga.list_reports()[:data.get("limit", 10)]
                            await manager.send_to_client(client_id, {"type": "game_analyzer_reports", "data": {"reports": reports}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "game_analyzer_error", "error": str(e)})

                elif msg_type == "adaptive_prompting":
                    try:
                        from sparkai.agent.agent_adaptive_prompting import get_adaptive_prompting, OptimizationStrategy, TaskCategory
                        ap = get_adaptive_prompting()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "adaptive_prompting_stats", "data": ap.get_stats()})
                        elif sub == "generate":
                            try:
                                category = TaskCategory(data.get("category", "game_design"))
                            except ValueError:
                                category = TaskCategory.GAME_DESIGN
                            try:
                                strategy = OptimizationStrategy(data.get("strategy", "epsilon_greedy"))
                            except ValueError:
                                strategy = OptimizationStrategy.EPSILON_GREEDY
                            result = ap.generate_prompt(category=category, variables=data.get("variables", {}), strategy=strategy)
                            await manager.broadcast_agent_event("prompt_generated", {"prompt": result.prompt_text, "variant_id": result.variant_id})
                        elif sub == "record_outcome":
                            ap.record_outcome(variant_id=data.get("variant_id", ""), score=data.get("score", 0.0), feedback=data.get("feedback"))
                            await manager.send_to_client(client_id, {"type": "outcome_recorded", "data": {"variant_id": data.get("variant_id", "")}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "adaptive_prompting_error", "error": str(e)})

                elif msg_type == "entity_extractor":
                    try:
                        from sparkai.agent.agent_entity_extraction import get_entity_extractor
                        ee = get_entity_extractor()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "entity_extractor_stats", "data": ee.get_stats()})
                        elif sub == "extract":
                            entities = ee.extract(text=data.get("text", ""), context=data.get("context"))
                            await manager.broadcast_agent_event("entities_extracted", {"entities": [e.to_dict() for e in entities], "count": len(entities)})
                        elif sub == "world_model":
                            model = ee.build_world_model(text=data.get("text", ""), context=data.get("context"))
                            await manager.broadcast_agent_event("world_model_built", model.to_dict())
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "entity_extractor_error", "error": str(e)})

                elif msg_type == "dialogue_system":
                    try:
                        from sparkai.engine.dialogue_system import get_dialogue_system, DialogueTree
                        ds = get_dialogue_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "dialogue_system_stats", "data": ds.get_stats()})
                        elif sub == "start":
                            result = ds.start_conversation(tree_id=data.get("tree_id", ""), session_id=data.get("session_id"))
                            await manager.broadcast_engine_status({"dialogue": result})
                        elif sub == "select":
                            result = ds.select_choice(session_id=data.get("session_id", ""), choice_id=data.get("choice_id", ""), context=data.get("context", {}))
                            await manager.broadcast_engine_status({"dialogue": result})
                        elif sub == "choices":
                            choices = ds.get_available_choices(data.get("session_id", ""))
                            await manager.send_to_client(client_id, {"type": "dialogue_choices", "data": {"choices": [c.to_dict() for c in choices]}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "dialogue_system_error", "error": str(e)})

                elif msg_type == "quest_system":
                    try:
                        from sparkai.engine.quest_system import get_quest_system, QuestDefinition, QuestObjective, QuestReward
                        qs = get_quest_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "quest_system_stats", "data": qs.get_stats()})
                        elif sub == "start":
                            success = qs.start_quest(quest_id=data.get("quest_id", ""), player_id=data.get("player_id", "default"))
                            await manager.broadcast_engine_status({"quest": {"started": success, "quest_id": data.get("quest_id", "")}})
                        elif sub == "update":
                            success = qs.update_objective(
                                quest_id=data.get("quest_id", ""),
                                player_id=data.get("player_id", "default"),
                                objective_index=data.get("objective_index", 0),
                                progress=data.get("progress", 1),
                            )
                            await manager.broadcast_engine_status({"quest": {"updated": success}})
                        elif sub == "complete":
                            result = qs.complete_quest(quest_id=data.get("quest_id", ""), player_id=data.get("player_id", "default"))
                            await manager.broadcast_engine_status({"quest": result})
                        elif sub == "active":
                            active = qs.get_active_quests(data.get("player_id", "default"))
                            await manager.send_to_client(client_id, {"type": "quest_active", "data": {"active_quests": [a.to_dict() for a in active]}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "quest_system_error", "error": str(e)})

                elif msg_type == "combat_system":
                    try:
                        from sparkai.engine.combat_system import get_combat_system, CombatMode, CombatActionType, CombatUnit, Element
                        cs = get_combat_system()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "combat_system_stats", "data": cs.get_stats()})
                        elif sub == "create_unit":
                            element = None
                            if data.get("element"):
                                try:
                                    element = Element(data.get("element"))
                                except ValueError:
                                    pass
                            unit = CombatUnit(
                                unit_id=data.get("unit_id", ""), name=data.get("name", ""),
                                hp=data.get("hp", 100), max_hp=data.get("max_hp", 100),
                                attack=data.get("attack", 10), defense=data.get("defense", 5),
                                speed=data.get("speed", 10), element=element,
                                team=data.get("team", "player"),
                            )
                            cs.create_unit(unit)
                            await manager.broadcast_engine_status({"combat": {"unit_created": data.get("unit_id", "")}})
                        elif sub == "initiate":
                            try:
                                mode = CombatMode(data.get("mode", "turn_based"))
                            except ValueError:
                                mode = CombatMode.TURN_BASED
                            state = cs.initiate_combat(team_a=data.get("team_a", []), team_b=data.get("team_b", []), mode=mode, combat_id=data.get("combat_id"))
                            await manager.broadcast_engine_status({"combat": state.to_dict()})
                        elif sub == "execute":
                            try:
                                action_type = CombatActionType(data.get("action_type", "attack"))
                            except ValueError:
                                action_type = CombatActionType.ATTACK
                            result = cs.execute_action(
                                combat_id=data.get("combat_id", ""), actor_id=data.get("actor_id", ""),
                                action_type=action_type, target_id=data.get("target_id"),
                                params=data.get("params"),
                            )
                            await manager.broadcast_engine_status({"combat": result.to_dict() if hasattr(result, 'to_dict') else result})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "combat_system_error", "error": str(e)})

                elif msg_type == "day_night_cycle":
                    try:
                        from sparkai.engine.day_night_cycle import get_day_night_cycle, DayNightConfig, TimeEvent
                        dnc = get_day_night_cycle()
                        sub = data.get("subtype", "stats")
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "day_night_stats", "data": dnc.get_stats()})
                        elif sub == "state":
                            await manager.send_to_client(client_id, {"type": "day_night_state", "data": {
                                "current_hour": dnc.get_current_hour(),
                                "current_phase": dnc.get_current_phase().value,
                            }})
                        elif sub == "lighting":
                            params = dnc.get_lighting_params()
                            await manager.send_to_client(client_id, {"type": "day_night_lighting", "data": params.to_dict() if hasattr(params, 'to_dict') else params})
                        elif sub == "configure":
                            config = DayNightConfig(
                                day_length_seconds=data.get("day_length_seconds", 300.0),
                                dawn_ratio=data.get("dawn_ratio", 0.1),
                                day_ratio=data.get("day_ratio", 0.45),
                                dusk_ratio=data.get("dusk_ratio", 0.1),
                                night_ratio=data.get("night_ratio", 0.35),
                                start_hour=data.get("start_hour", 6.0),
                            )
                            dnc.configure(config)
                            await manager.broadcast_engine_status({"day_night": {"configured": True}})
                        elif sub == "update":
                            dnc.update(data.get("delta_seconds", 1.0))
                            await manager.broadcast_engine_status({"day_night": {"updated": True, "hour": dnc.get_current_hour()}})
                        elif sub == "schedule_event":
                            event = TimeEvent(
                                event_id=data.get("event_id", ""), trigger_hour=data.get("trigger_hour", 0.0),
                                callback_name=data.get("callback_name", ""), data=data.get("event_data"),
                                repeat=data.get("repeat", False),
                            )
                            dnc.schedule_event(event)
                            await manager.send_to_client(client_id, {"type": "day_night_event_scheduled", "data": {"event_id": data.get("event_id", "")}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "day_night_error", "error": str(e)})

                elif msg_type == "style_transfer":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.agent.agent_style_transfer import get_style_transfer, StyleDomain, TransferIntensity
                        st = get_style_transfer()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "style_transfer_stats", "data": st.get_stats()})
                        elif sub == "list":
                            domain = None
                            if data.get("domain"):
                                try:
                                    domain = StyleDomain(data.get("domain"))
                                except ValueError:
                                    pass
                            styles = st.list_styles(domain)
                            await manager.send_to_client(client_id, {"type": "style_transfer_list", "data": [s.to_dict() for s in styles]})
                        elif sub == "transfer":
                            domain = StyleDomain(data.get("domain", "visual"))
                            intensity = TransferIntensity(data.get("intensity", "moderate"))
                            result = st.transfer_style(
                                source_content=data.get("source", ""),
                                source_style_id=data.get("source_style_id", ""),
                                target_style_id=data.get("target_style_id", ""),
                                domain=domain,
                                intensity=intensity,
                            )
                            await manager.broadcast_agent_event("style_transferred", result.to_dict())
                        elif sub == "history":
                            history = st.get_transfer_history(data.get("limit", 20))
                            await manager.send_to_client(client_id, {"type": "style_transfer_history", "data": history})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "style_transfer_error", "error": str(e)})

                elif msg_type == "curriculum_learning":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.agent.agent_curriculum_learning import get_curriculum_learning, LearningStrategy, SkillLevel
                        cl = get_curriculum_learning()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "curriculum_learning_stats", "data": cl.get_stats()})
                        elif sub == "start_session":
                            strat = LearningStrategy(data.get("strategy", "scaffolded"))
                            cl.set_strategy(strat)
                            session = cl.start_session(
                                player_id=data.get("player_id", "default"),
                                initial_skill_level=SkillLevel(data.get("skill_level", "beginner")),
                            )
                            await manager.broadcast_agent_event("curriculum_session_started", session)
                        elif sub == "record_performance":
                            cl.record_performance(
                                skill_id=data.get("skill_id", ""),
                                accuracy=data.get("accuracy", 0.0),
                                completion_time=data.get("completion_time", 0.0),
                                attempts=data.get("attempts", 1),
                            )
                            await manager.send_to_client(client_id, {"type": "curriculum_performance_recorded", "data": {"skill_id": data.get("skill_id", "")}})
                        elif sub == "recommended":
                            skills = cl.get_recommended_skills(data.get("count", 3))
                            await manager.send_to_client(client_id, {"type": "curriculum_recommended", "data": [s.to_dict() for s in skills]})
                        elif sub == "graph":
                            graph = cl.get_skill_graph()
                            await manager.send_to_client(client_id, {"type": "curriculum_graph", "data": graph})
                        elif sub == "end_session":
                            result = cl.end_session()
                            await manager.broadcast_agent_event("curriculum_session_ended", result or {})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "curriculum_learning_error", "error": str(e)})

                elif msg_type == "balancing":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.agent.agent_balancing import get_game_balancer, TuningDomain
                        gb = get_game_balancer()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "balancing_stats", "data": gb.get_stats()})
                        elif sub == "analyze":
                            domain = TuningDomain(data.get("domain", "combat"))
                            report = gb.analyze_domain(domain)
                            await manager.broadcast_agent_event("balance_analyzed", report.to_dict())
                        elif sub == "analyze_all":
                            reports = gb.analyze_all()
                            await manager.broadcast_agent_event("balance_all_analyzed",
                                {k.value: v.to_dict() for k, v in reports.items()})
                        elif sub == "parameters":
                            domain = None
                            if data.get("domain"):
                                try:
                                    domain = TuningDomain(data.get("domain"))
                                except ValueError:
                                    pass
                            snapshot = gb.get_parameter_snapshot(domain)
                            await manager.send_to_client(client_id, {"type": "balancing_parameters", "data": snapshot})
                        elif sub == "report_metric":
                            from sparkai.agent.agent_balancing import BalanceMetric
                            metric = BalanceMetric(
                                domain=TuningDomain(data.get("domain", "combat")),
                                metric_name=data.get("metric_name", ""),
                                value=data.get("value", 0.0),
                                target_min=data.get("target_min"),
                                target_max=data.get("target_max"),
                            )
                            gb.report_metric(metric)
                            await manager.send_to_client(client_id, {"type": "balancing_metric_reported", "data": {"metric_name": data.get("metric_name", "")}})
                        elif sub == "apply_tuning":
                            domain = TuningDomain(data.get("domain", "combat"))
                            report = gb.analyze_domain(domain)
                            changes = gb.apply_tuning(report)
                            await manager.broadcast_agent_event("balance_tuned", {"changes": changes, "domain": domain.value})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "balancing_error", "error": str(e)})

                elif msg_type == "content_localization":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.agent.agent_localization import get_localization_engine, Locale, StringCategory
                        le = get_localization_engine()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "content_localization_stats", "data": le.get_stats()})
                        elif sub == "locales":
                            locales = le.get_supported_locales()
                            await manager.send_to_client(client_id, {"type": "content_localization_locales", "data": [l.value for l in locales]})
                        elif sub == "register_string":
                            cat = StringCategory(data.get("category", "ui_label"))
                            string_id = le.register_string_by_key(
                                key=data.get("key", ""),
                                source_text=data.get("source_text", ""),
                                category=cat,
                                context=data.get("context"),
                            )
                            await manager.send_to_client(client_id, {"type": "content_localization_registered", "data": {"string_id": string_id}})
                        elif sub == "get_text":
                            locale = Locale(data.get("locale", "en"))
                            text = le.get_text(data.get("string_id", ""), locale)
                            await manager.send_to_client(client_id, {"type": "content_localization_text", "data": {"text": text}})
                        elif sub == "completeness":
                            locale = Locale(data.get("locale", "en"))
                            pct = le.get_completeness(locale)
                            await manager.send_to_client(client_id, {"type": "content_localization_completeness", "data": {"locale": locale.value, "completeness": pct}})
                        elif sub == "missing":
                            locale = Locale(data.get("locale", "en"))
                            missing = le.get_missing_translations(locale)
                            await manager.send_to_client(client_id, {"type": "content_localization_missing",
                                "data": {"locale": locale.value, "missing_count": len(missing), "strings": [s.to_dict() for s in missing[:20]]}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "content_localization_error", "error": str(e)})

                elif msg_type == "tutorial_design":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.agent.agent_tutorial_design import get_tutorial_designer, ScaffoldingTier
                        td = get_tutorial_designer()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "tutorial_design_stats", "data": td.get_stats()})
                        elif sub == "design":
                            from sparkai.agent.agent_tutorial_design import MechanicDefinition
                            mech = MechanicDefinition(
                                mechanic_id=data.get("mechanic_id", ""),
                                name=data.get("name", ""),
                                description=data.get("description", ""),
                                complexity=data.get("complexity", 0.5),
                                category=data.get("category", "core"),
                                prerequisites=data.get("prerequisites", []),
                            )
                            td.define_mechanic(mech)
                            tier = ScaffoldingTier(data.get("tier", "guided"))
                            sequence = td.design_tutorial(mech.mechanic_id, tier)
                            await manager.broadcast_agent_event("tutorial_designed", sequence.to_dict())
                        elif sub == "mechanics":
                            mechanics = td.get_all_mechanics_ordered()
                            await manager.send_to_client(client_id, {"type": "tutorial_mechanics", "data": [m.to_dict() for m in mechanics]})
                        elif sub == "next":
                            next_mech = td.get_next_recommended_tutorial()
                            await manager.send_to_client(client_id, {"type": "tutorial_next", "data": next_mech.to_dict() if next_mech else None})
                        elif sub == "complete":
                            td.record_completion(data.get("sequence_id", ""), data.get("completion_time", 0.0))
                            await manager.send_to_client(client_id, {"type": "tutorial_completed", "data": {"sequence_id": data.get("sequence_id", "")}})
                        elif sub == "skip":
                            td.record_skip(data.get("sequence_id", ""))
                            await manager.send_to_client(client_id, {"type": "tutorial_skipped", "data": {"sequence_id": data.get("sequence_id", "")}})
                        elif sub == "adjust_tier":
                            tier = td.adjust_tier(data.get("mechanic_id", ""))
                            await manager.send_to_client(client_id, {"type": "tutorial_tier_adjusted", "data": {"mechanic_id": data.get("mechanic_id", ""), "tier": tier.value}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "tutorial_design_error", "error": str(e)})

                elif msg_type == "game_testing":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.agent.agent_game_testing import get_game_tester, TestType, TestSeverity
                        gt = get_game_tester()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "game_testing_stats", "data": gt.get_stats()})
                        elif sub == "create_run":
                            test_types = [TestType(t) for t in data.get("test_types", ["smoke"])]
                            run_id = gt.create_test_run(
                                game_id=data.get("game_id", "default"),
                                test_types=test_types,
                                max_duration=data.get("max_duration", 60.0),
                                parameters=data.get("parameters"),
                            )
                            await manager.broadcast_agent_event("test_run_created", {"run_id": run_id})
                        elif sub == "run":
                            test_types = [TestType(t) for t in data.get("test_types", ["smoke"])]
                            results = gt.run_tests(
                                game_id=data.get("game_id", "default"),
                                test_types=test_types,
                                max_duration=data.get("max_duration", 60.0),
                            )
                            await manager.broadcast_agent_event("tests_completed", results or {})
                        elif sub == "results":
                            results = gt.get_latest_results()
                            await manager.send_to_client(client_id, {"type": "game_testing_results", "data": results})
                        elif sub == "coverage":
                            report = gt.get_coverage_report()
                            await manager.send_to_client(client_id, {"type": "game_testing_coverage", "data": report})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "game_testing_error", "error": str(e)})

                elif msg_type == "weather":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.engine.weather_system import get_weather_system, WeatherState
                        ws = get_weather_system()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "weather_stats", "data": ws.get_stats()})
                        elif sub == "zones":
                            zones = ws.get_all_zones()
                            await manager.send_to_client(client_id, {"type": "weather_zones", "data": zones})
                        elif sub == "set":
                            state = WeatherState(data.get("state", "clear"))
                            ws.set_weather(data.get("zone_id", ""), state)
                            await manager.broadcast_engine_status({"weather": {"zone_id": data.get("zone_id", ""), "state": state.value}})
                        elif sub == "randomize":
                            state = ws.randomize_weather(data.get("zone_id", ""))
                            await manager.broadcast_engine_status({"weather": {"zone_id": data.get("zone_id", ""), "state": state.value if state else "unknown"}})
                        elif sub == "update":
                            ws.update(data.get("delta_seconds", 0.016))
                            state = ws.get_current_state(data.get("zone_id", ""))
                            await manager.broadcast_engine_status({"weather": {"updated": True, "state": state.value if state else "unknown"}})
                        elif sub == "modifiers":
                            modifiers = ws.get_gameplay_modifiers(data.get("zone_id", ""))
                            await manager.send_to_client(client_id, {"type": "weather_modifiers", "data": modifiers})
                        elif sub == "params":
                            params = ws.get_current_params(data.get("zone_id", ""))
                            if params:
                                await manager.send_to_client(client_id, {"type": "weather_params", "data": params.to_dict()})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "weather_error", "error": str(e)})

                elif msg_type == "skill_tree":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.engine.skill_tree_system import get_skill_tree_system, NodeType, NodeState
                        sts = get_skill_tree_system()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "skill_tree_stats", "data": sts.get_stats()})
                        elif sub == "create_character":
                            char = sts.create_character(data.get("character_id", ""), data.get("initial_points", 0))
                            await manager.broadcast_engine_status({"skill_tree": {"character_created": data.get("character_id", ""), "points": char.available_points}})
                        elif sub == "add_points":
                            total = sts.add_points(data.get("character_id", ""), data.get("points", 1))
                            await manager.send_to_client(client_id, {"type": "skill_tree_points_added", "data": {"character_id": data.get("character_id", ""), "total_points": total}})
                        elif sub == "unlock":
                            result = sts.unlock_node(data.get("character_id", ""), data.get("node_id", ""))
                            await manager.broadcast_engine_status({"skill_tree": result})
                        elif sub == "available":
                            nodes = sts.get_available_nodes(data.get("character_id", ""), data.get("tree_id"))
                            await manager.send_to_client(client_id, {"type": "skill_tree_available", "data": [n.to_dict() for n in nodes]})
                        elif sub == "summary":
                            summary = sts.get_tree_summary(data.get("tree_id", ""))
                            await manager.send_to_client(client_id, {"type": "skill_tree_summary", "data": summary})
                        elif sub == "modifiers":
                            mods = sts.get_unlocked_modifiers(data.get("character_id", ""))
                            await manager.send_to_client(client_id, {"type": "skill_tree_modifiers", "data": mods})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "skill_tree_error", "error": str(e)})

                elif msg_type == "crafting":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.engine.crafting_system import get_crafting_system, QualityTier, CraftingCategory
                        cs = get_crafting_system()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "crafting_stats", "data": cs.get_stats()})
                        elif sub == "craft":
                            result = cs.craft(
                                character_id=data.get("character_id", "default"),
                                recipe_id=data.get("recipe_id", ""),
                                provided_ingredients=data.get("ingredients", []),
                                luck_modifier=data.get("luck", 0.0),
                            )
                            await manager.broadcast_engine_status({"crafting": result.to_dict()})
                        elif sub == "discover":
                            discovered = cs.discover_recipes(
                                character_id=data.get("character_id", "default"),
                                skill_category=CraftingCategory(data.get("category", "smithing")),
                            )
                            await manager.broadcast_engine_status({"crafting": {"discovered": len(discovered)}})
                        elif sub == "available":
                            recipes = cs.get_available_recipes(data.get("character_id", "default"))
                            await manager.send_to_client(client_id, {"type": "crafting_available", "data": [r.to_dict() for r in recipes]})
                        elif sub == "learn":
                            success = cs.learn_recipe(data.get("character_id", "default"), data.get("recipe_id", ""))
                            await manager.send_to_client(client_id, {"type": "crafting_learned", "data": {"success": success}})
                        elif sub == "improve":
                            level = cs.improve_skill(data.get("character_id", "default"), data.get("category", "all"), data.get("xp", 10))
                            await manager.send_to_client(client_id, {"type": "crafting_skill_improved", "data": {"level": level}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "crafting_error", "error": str(e)})

                elif msg_type == "loot":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.engine.loot_system import get_loot_system, Rarity, LootCategory
                        ls = get_loot_system()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "loot_stats", "data": ls.get_stats()})
                        elif sub == "generate":
                            items = ls.generate_loot(
                                table_id=data.get("table_id", ""),
                                luck_modifier=data.get("luck", 0.0),
                                level=data.get("level", 1),
                                count=data.get("count", 1),
                            )
                            await manager.broadcast_engine_status({"loot": {"generated": len(items), "items": [i.to_dict() for i in items]}})
                        elif sub == "roll_rarity":
                            rarity = ls.roll_rarity(data.get("luck", 0.0))
                            color = ls.get_rarity_color(rarity)
                            await manager.send_to_client(client_id, {"type": "loot_rarity_rolled", "data": {"rarity": rarity.value, "color": color}})
                        elif sub == "rarity_colors":
                            colors = {r.value: ls.get_rarity_color(r) for r in Rarity}
                            await manager.send_to_client(client_id, {"type": "loot_rarity_colors", "data": colors})
                        elif sub == "rarity_weights":
                            weights = ls.get_rarity_weights()
                            await manager.send_to_client(client_id, {"type": "loot_rarity_weights", "data": weights})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "loot_error", "error": str(e)})

                elif msg_type == "economy":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.engine.economy_system import get_economy_system, CurrencyType, TradeType
                        es = get_economy_system()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "economy_stats", "data": es.get_stats()})
                        elif sub == "wallet":
                            summary = es.get_wallet_summary(data.get("owner_id", ""))
                            await manager.send_to_client(client_id, {"type": "economy_wallet", "data": summary})
                        elif sub == "add":
                            currency = CurrencyType(data.get("currency", "gold"))
                            new_balance = es.add_currency(data.get("owner_id", ""), currency, data.get("amount", 0.0))
                            await manager.broadcast_engine_status({"economy": {"owner_id": data.get("owner_id", ""), "currency": currency.value, "new_balance": new_balance}})
                        elif sub == "remove":
                            currency = CurrencyType(data.get("currency", "gold"))
                            success = es.remove_currency(data.get("owner_id", ""), currency, data.get("amount", 0.0))
                            await manager.send_to_client(client_id, {"type": "economy_removed", "data": {"success": success}})
                        elif sub == "market":
                            summary = es.get_market_summary()
                            await manager.send_to_client(client_id, {"type": "economy_market", "data": summary})
                        elif sub == "trade":
                            result = es.execute_trade(
                                buyer_id=data.get("buyer_id", ""),
                                seller_id=data.get("seller_id", ""),
                                item_id=data.get("item_id", ""),
                                currency=CurrencyType(data.get("currency", "gold")),
                                quantity=data.get("quantity", 1),
                                price=data.get("price", 0.0),
                            )
                            await manager.broadcast_engine_status({"economy": result.to_dict() if result else {"error": "Trade failed"}})
                        elif sub == "convert":
                            result = es.convert_currency(
                                data.get("owner_id", ""),
                                CurrencyType(data.get("from_currency", "gold")),
                                CurrencyType(data.get("to_currency", "silver")),
                                data.get("amount", 0.0),
                            )
                            if result:
                                await manager.send_to_client(client_id, {"type": "economy_converted", "data": result.to_dict()})
                        elif sub == "update_market":
                            es.update_market(data.get("delta_time", 1.0))
                            await manager.send_to_client(client_id, {"type": "economy_market_updated", "data": {"success": True}})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "economy_error", "error": str(e)})

                elif msg_type == "cutscene":
                    sub = data.get("subtype", "stats")
                    try:
                        from sparkai.engine.cutscene_system import get_cutscene_system
                        cut = get_cutscene_system()
                        if sub == "stats":
                            await manager.send_to_client(client_id, {"type": "cutscene_stats", "data": cut.get_stats()})
                        elif sub == "play":
                            success = cut.play(data.get("scene_id", ""), data.get("start_time", 0.0))
                            await manager.broadcast_engine_status({"cutscene": {"playing": success, "scene_id": data.get("scene_id", "")}})
                        elif sub == "update":
                            state = cut.update(data.get("delta_seconds", 0.016))
                            await manager.broadcast_engine_status({"cutscene": state})
                        elif sub == "skip":
                            success = cut.skip()
                            await manager.broadcast_engine_status({"cutscene": {"skipped": success}})
                        elif sub == "skip_to_chapter":
                            success = cut.skip_to_chapter(data.get("chapter_name", ""))
                            await manager.broadcast_engine_status({"cutscene": {"skipped_to_chapter": success}})
                        elif sub == "pause":
                            cut.pause()
                            await manager.broadcast_engine_status({"cutscene": {"paused": True}})
                        elif sub == "resume":
                            cut.resume()
                            await manager.broadcast_engine_status({"cutscene": {"resumed": True}})
                        elif sub == "stop":
                            cut.stop()
                            await manager.broadcast_engine_status({"cutscene": {"stopped": True}})
                        elif sub == "state":
                            state = cut.get_current_state()
                            await manager.send_to_client(client_id, {"type": "cutscene_state", "data": state})
                    except Exception as e:
                        await manager.send_to_client(client_id, {"type": "cutscene_error", "error": str(e)})

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
