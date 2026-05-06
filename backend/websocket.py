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
