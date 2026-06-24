"""
SparkLabs API Routes for Gateway, Timeline, God Mode, Scene Tree,
Server Registry, and Component System.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import time

router = APIRouter(tags=["Agent Core Systems"])


# ── Gateway Routes ──────────────────────────────────────────────────────────

@router.get("/gateway/status")
async def gateway_status():
    """Get the current status of the Agent Gateway."""
    try:
        from sparkai.agent.agent_gateway import AgentGateway, get_agent_gateway
        gateway = get_agent_gateway()
        if not gateway._initialized:
            gateway.initialize()
        status = gateway.get_status()
        return JSONResponse({"status": "success", "data": status})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/gateway/metrics")
async def gateway_metrics():
    """Get gateway performance metrics."""
    try:
        from sparkai.agent.agent_gateway import get_agent_gateway
        gateway = get_agent_gateway()
        if not gateway._initialized:
            gateway.initialize()
        metrics = gateway.get_metrics()
        return JSONResponse({"status": "success", "data": metrics})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/gateway/route")
async def gateway_route(request: Request):
    """Route a request through the Agent Gateway."""
    try:
        from sparkai.agent.agent_gateway import get_agent_gateway, GatewayMode, ProviderType
        body = await request.json()
        prompt = body.get("prompt", "")
        context = body.get("context", {})
        mode_str = body.get("mode", "auto_route")
        provider_str = body.get("provider", None)
        # Convert string to enum
        try:
            mode = GatewayMode(mode_str)
        except ValueError:
            mode = GatewayMode.AUTO_ROUTE
        provider = ProviderType(provider_str) if provider_str else None
        gateway = get_agent_gateway()
        if not gateway._initialized:
            gateway.initialize()
        result = gateway.route_request(prompt, context, mode, provider)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/gateway/providers")
async def gateway_providers():
    """List available gateway providers."""
    try:
        from sparkai.agent.agent_gateway import get_agent_gateway
        gateway = get_agent_gateway()
        if not gateway._initialized:
            gateway.initialize()
        providers = gateway.list_providers()
        return JSONResponse({"status": "success", "data": providers})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/gateway/history")
async def gateway_history(limit: int = Query(default=20, le=100)):
    """Get recent gateway request history."""
    try:
        from sparkai.agent.agent_gateway import get_agent_gateway
        gateway = get_agent_gateway()
        if not gateway._initialized:
            gateway.initialize()
        history = gateway.get_request_history()[-limit:]
        return JSONResponse({"status": "success", "data": [h.to_dict() for h in history]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── Timeline Routes ─────────────────────────────────────────────────────────

@router.get("/timeline/status")
async def timeline_status():
    """Get the current status of the Timeline Manager."""
    try:
        from sparkai.agent.agent_timeline import get_timeline_manager
        tm = get_timeline_manager()
        if not tm._initialized:
            tm.initialize()
        status = tm.get_status()
        return JSONResponse({"status": "success", "data": status})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/timeline-core/create")
async def timeline_create(request: Request):
    """Create a new timeline."""
    try:
        from sparkai.agent.agent_timeline import get_timeline_manager
        body = await request.json()
        name = body.get("name", f"Timeline-{int(time.time())}")
        description = body.get("description", "")
        metadata = body.get("metadata", {})
        tm = get_timeline_manager()
        if not tm._initialized:
            tm.initialize()
        result = tm.create_timeline(name, description, metadata)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/timeline/list")
async def timeline_list():
    """List all timelines."""
    try:
        from sparkai.agent.agent_timeline import get_timeline_manager
        tm = get_timeline_manager()
        if not tm._initialized:
            tm.initialize()
        timelines = tm.list_timelines()
        return JSONResponse({"status": "success", "data": [t.to_dict() for t in timelines]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/timeline/{timeline_id}")
async def timeline_get(timeline_id: str):
    """Get a specific timeline by ID."""
    try:
        from sparkai.agent.agent_timeline import get_timeline_manager
        tm = get_timeline_manager()
        if not tm._initialized:
            tm.initialize()
        timeline = tm.get_timeline(timeline_id)
        if not timeline:
            return JSONResponse({"status": "error", "message": "Timeline not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": timeline.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/timeline/{timeline_id}/event")
async def timeline_record_event(timeline_id: str, request: Request):
    """Record an event on a timeline."""
    try:
        from sparkai.agent.agent_timeline import get_timeline_manager
        body = await request.json()
        event_type = body.get("event_type", "generic")
        description = body.get("description", "")
        agent_id = body.get("agent_id", "system")
        data = body.get("data", {})
        tm = get_timeline_manager()
        if not tm._initialized:
            tm.initialize()
        event = tm.record_event(timeline_id, event_type, description, agent_id, data)
        if not event:
            return JSONResponse({"status": "error", "message": "Timeline not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": event.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/timeline/{timeline_id}/branch")
async def timeline_create_branch(timeline_id: str, request: Request):
    """Create a branch from a timeline."""
    try:
        from sparkai.agent.agent_timeline import get_timeline_manager
        body = await request.json()
        branch_name = body.get("branch_name", f"Branch-{int(time.time())}")
        description = body.get("description", "")
        tm = get_timeline_manager()
        if not tm._initialized:
            tm.initialize()
        result = tm.create_branch(timeline_id, branch_name, description)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/timeline/merge")
async def timeline_merge(request: Request):
    """Merge two timelines."""
    try:
        from sparkai.agent.agent_timeline import get_timeline_manager
        body = await request.json()
        source_id = body.get("source_id")
        target_id = body.get("target_id")
        if not source_id or not target_id:
            return JSONResponse({"status": "error", "message": "source_id and target_id required"}, status_code=400)
        tm = get_timeline_manager()
        if not tm._initialized:
            tm.initialize()
        result = tm.merge_timelines(source_id, target_id)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── God Mode Routes ─────────────────────────────────────────────────────────

@router.get("/god-mode/status")
async def god_mode_status():
    """Get the current status of the God Mode Controller."""
    try:
        from sparkai.agent.agent_god_mode import get_god_mode_controller
        gm = get_god_mode_controller()
        if not gm._initialized:
            gm.initialize()
        status = gm.get_status()
        return JSONResponse({"status": "success", "data": status})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/god-mode/observe-agent")
async def god_mode_observe_agent(request: Request):
    """Observe an agent's detailed state."""
    try:
        from sparkai.agent.agent_god_mode import get_god_mode_controller
        body = await request.json()
        agent_id = body.get("agent_id", "")
        gm = get_god_mode_controller()
        if not gm._initialized:
            gm.initialize()
        data = gm.observe_agent(agent_id)
        return JSONResponse({"status": "success", "data": data})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/god-mode/observe-world")
async def god_mode_observe_world(request: Request):
    """Observe a world's detailed state."""
    try:
        from sparkai.agent.agent_god_mode import get_god_mode_controller
        body = await request.json()
        world_id = body.get("world_id", "")
        gm = get_god_mode_controller()
        if not gm._initialized:
            gm.initialize()
        data = gm.observe_world(world_id)
        return JSONResponse({"status": "success", "data": data})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/god-mode-core/edit-memory")
async def god_mode_edit_memory(request: Request):
    """Edit an agent's memory."""
    try:
        from sparkai.agent.agent_god_mode import get_god_mode_controller
        body = await request.json()
        agent_id = body.get("agent_id", "")
        memory_key = body.get("memory_key", "")
        new_value = body.get("new_value", "")
        operation = body.get("operation", "UPDATE")
        gm = get_god_mode_controller()
        if not gm._initialized:
            gm.initialize()
        result = gm.edit_agent_memory(agent_id, memory_key, new_value, operation)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/god-mode/edit-personality")
async def god_mode_edit_personality(request: Request):
    """Edit an agent's personality trait."""
    try:
        from sparkai.agent.agent_god_mode import get_god_mode_controller
        body = await request.json()
        agent_id = body.get("agent_id", "")
        trait_name = body.get("trait_name", "")
        new_value = body.get("new_value", 0.5)
        gm = get_god_mode_controller()
        if not gm._initialized:
            gm.initialize()
        result = gm.edit_agent_personality(agent_id, trait_name, new_value)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/god-mode-core/inject-event")
async def god_mode_inject_event(request: Request):
    """Inject a world event."""
    try:
        from sparkai.agent.agent_god_mode import get_god_mode_controller
        body = await request.json()
        event_type = body.get("event_type", "generic")
        description = body.get("description", "")
        target_location = body.get("target_location", "")
        affected_agents = body.get("affected_agents", [])
        intensity = body.get("intensity", 0.5)
        gm = get_god_mode_controller()
        if not gm._initialized:
            gm.initialize()
        result = gm.inject_world_event(event_type, description, target_location, affected_agents, intensity)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/god-mode/broadcast")
async def god_mode_broadcast(request: Request):
    """Broadcast a message to agents."""
    try:
        from sparkai.agent.agent_god_mode import get_god_mode_controller
        body = await request.json()
        message = body.get("message", "")
        scope = body.get("scope", "ALL_AGENTS")
        target_ids = body.get("target_ids", [])
        gm = get_god_mode_controller()
        if not gm._initialized:
            gm.initialize()
        result = gm.broadcast_message(message, scope, target_ids)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── Scene Tree Routes ───────────────────────────────────────────────────────

@router.get("/scene-tree/status")
async def scene_tree_status():
    """Get the current status of the Scene Tree."""
    try:
        from sparkai.engine.engine_scene_tree import get_scene_tree
        st = get_scene_tree()
        if not st._initialized:
            st.initialize()
        status = st.get_status()
        return JSONResponse({"status": "success", "data": status})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/scene-tree/node")
async def scene_tree_create_node(request: Request):
    """Create a new node in the scene tree."""
    try:
        from sparkai.engine.engine_scene_tree import get_scene_tree, NodeType
        body = await request.json()
        name = body.get("name", f"Node-{int(time.time())}")
        node_type_str = body.get("node_type", "ENTITY")
        try:
            node_type = NodeType(node_type_str.lower())
        except ValueError:
            node_type = NodeType.ENTITY
        parent_id = body.get("parent_id", None)
        position = body.get("position", {"x": 0, "y": 0, "z": 0})
        rotation = body.get("rotation", {"x": 0, "y": 0, "z": 0})
        scale = body.get("scale", {"x": 1, "y": 1, "z": 1})
        st = get_scene_tree()
        if not st._initialized:
            st.initialize()
        node = st.create_node(name, node_type, parent_id, position, rotation, scale)
        if node is None:
            return JSONResponse({"status": "error", "message": "Failed to create node: scene tree not initialized or parent not found"}, status_code=400)
        return JSONResponse({"status": "success", "data": node.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/scene-tree/node/{node_id}")
async def scene_tree_get_node(node_id: str):
    """Get a node by ID."""
    try:
        from sparkai.engine.engine_scene_tree import get_scene_tree
        st = get_scene_tree()
        if not st._initialized:
            st.initialize()
        node = st.get_node(node_id)
        if not node:
            return JSONResponse({"status": "error", "message": "Node not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": node.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/scene-tree/node/{node_id}")
async def scene_tree_remove_node(node_id: str):
    """Remove a node from the scene tree."""
    try:
        from sparkai.engine.engine_scene_tree import get_scene_tree
        st = get_scene_tree()
        if not st._initialized:
            st.initialize()
        success = st.remove_node(node_id)
        return JSONResponse({"status": "success", "data": {"removed": success}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/scene-tree/graph")
async def scene_tree_graph():
    """Get the full scene graph."""
    try:
        from sparkai.engine.engine_scene_tree import get_scene_tree
        st = get_scene_tree()
        if not st._initialized:
            st.initialize()
        graph = st.get_scene_graph()
        return JSONResponse({"status": "success", "data": graph})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/scene-tree/find-by-tag")
async def scene_tree_find_by_tag(tag: str = Query(...)):
    """Find nodes by tag."""
    try:
        from sparkai.engine.engine_scene_tree import get_scene_tree
        st = get_scene_tree()
        if not st._initialized:
            st.initialize()
        nodes = st.find_by_tag(tag)
        return JSONResponse({"status": "success", "data": [n.to_dict() for n in nodes]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── Server Registry Routes ──────────────────────────────────────────────────

@router.get("/server-registry/status")
async def server_registry_status():
    """Get the current status of the Server Registry."""
    try:
        from sparkai.engine.engine_server_registry import get_engine_server_registry
        sr = get_engine_server_registry()
        if not sr._is_initialized:
            sr.initialize()
        status = sr.get_status()
        return JSONResponse({"status": "success", "data": status})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/server-registry/servers")
async def server_registry_servers():
    """List all registered servers."""
    try:
        from sparkai.engine.engine_server_registry import get_engine_server_registry
        sr = get_engine_server_registry()
        if not sr._is_initialized:
            sr.initialize()
        servers = sr.get_all_servers()
        return JSONResponse({"status": "success", "data": [s.to_dict() for s in servers]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/server-registry/start/{server_type}")
async def server_registry_start(server_type: str):
    """Start a specific server."""
    try:
        from sparkai.engine.engine_server_registry import get_engine_server_registry, ServerType
        sr = get_engine_server_registry()
        if not sr._is_initialized:
            sr.initialize()
        st = ServerType(server_type.lower())
        success = sr.start_server(st)
        if not success:
            return JSONResponse({"status": "error", "message": f"Failed to start server {server_type}"}, status_code=400)
        return JSONResponse({"status": "success", "data": {"server_type": server_type.lower(), "status": "running"}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/server-registry/stop/{server_type}")
async def server_registry_stop(server_type: str):
    """Stop a specific server."""
    try:
        from sparkai.engine.engine_server_registry import get_engine_server_registry, ServerType
        sr = get_engine_server_registry()
        if not sr._is_initialized:
            sr.initialize()
        st = ServerType(server_type.lower())
        success = sr.stop_server(st)
        if not success:
            return JSONResponse({"status": "error", "message": f"Failed to stop server {server_type}"}, status_code=400)
        return JSONResponse({"status": "success", "data": {"server_type": server_type.lower(), "status": "stopped"}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/server-registry/start-all")
async def server_registry_start_all():
    """Start all registered servers."""
    try:
        from sparkai.engine.engine_server_registry import get_engine_server_registry
        sr = get_engine_server_registry()
        if not sr._is_initialized:
            sr.initialize()
        results = sr.start_all()
        return JSONResponse({"status": "success", "data": results})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── Component System Routes ─────────────────────────────────────────────────

@router.get("/component-system/status")
async def component_system_status():
    """Get the current status of the Component Registry."""
    try:
        from sparkai.engine.engine_component_system import get_component_registry
        cr = get_component_registry()
        if not cr._initialized:
            cr.initialize()
        status = cr.get_status()
        return JSONResponse({"status": "success", "data": status})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/component-system/definitions")
async def component_system_definitions():
    """List all component definitions."""
    try:
        from sparkai.engine.engine_component_system import get_component_registry
        cr = get_component_registry()
        if not cr._initialized:
            cr.initialize()
        defs = cr.list_component_definitions()
        return JSONResponse({"status": "success", "data": [d.to_dict() for d in defs]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/component-system/entity")
async def component_system_create_entity(request: Request):
    """Create a new game entity."""
    try:
        from sparkai.engine.engine_component_system import get_component_registry
        body = await request.json()
        name = body.get("name", f"Entity-{int(time.time())}")
        entity_type = body.get("entity_type", "generic")
        cr = get_component_registry()
        if not cr._initialized:
            cr.initialize()
        entity = cr.create_entity(name, entity_type)
        return JSONResponse({"status": "success", "data": entity.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/component-system/entity/{entity_id}")
async def component_system_get_entity(entity_id: str):
    """Get an entity by ID."""
    try:
        from sparkai.engine.engine_component_system import get_component_registry
        cr = get_component_registry()
        if not cr._initialized:
            cr.initialize()
        entity = cr.get_entity(entity_id)
        if not entity:
            return JSONResponse({"status": "error", "message": "Entity not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": entity.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/component-system/entity/{entity_id}/component")
async def component_system_add_component(entity_id: str, request: Request):
    """Add a component to an entity."""
    try:
        from sparkai.engine.engine_component_system import get_component_registry
        body = await request.json()
        definition_id = body.get("definition_id", "")
        properties = body.get("properties", {})
        cr = get_component_registry()
        if not cr._initialized:
            cr.initialize()
        comp = cr.add_component(entity_id, definition_id, properties)
        if not comp:
            return JSONResponse({"status": "error", "message": "Failed to add component"}, status_code=400)
        return JSONResponse({"status": "success", "data": comp.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)