"""
SparkLabs Unified API Routes for Action Space, Self-Reflection, Reasoning Chain,
Task Decomposer, Perception Pipeline, Event Bus, Tile Map, Prefab System,
Input Action System, and Shader Material System.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import time

router = APIRouter(tags=["Agent & Engine Unified Systems"])


# ═══════════════════════════════════════════════════════════════════════════════
# Action Space Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/action-space/status")
async def action_space_status():
    """Get the current status of the Action Space Engine."""
    try:
        from sparkai.agent.agent_action_space import ActionSpaceEngine
        ae = ActionSpaceEngine.get_instance()
        if not ae._initialized:
            ae.initialize()
        return JSONResponse({"status": "success", "data": ae.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/action-space/actions")
async def action_space_list_actions():
    """List all registered actions."""
    try:
        from sparkai.agent.agent_action_space import ActionSpaceEngine
        ae = ActionSpaceEngine.get_instance()
        if not ae._initialized:
            ae.initialize()
        actions = ae.list_actions()
        return JSONResponse({"status": "success", "data": actions})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/action-space/execute")
async def action_space_execute(request: Request):
    """Execute a named action."""
    try:
        from sparkai.agent.agent_action_space import ActionSpaceEngine
        body = await request.json()
        action_name = body.get("action_name", "")
        parameters = body.get("parameters", {})
        context = body.get("context", None)
        ae = ActionSpaceEngine.get_instance()
        if not ae._initialized:
            ae.initialize()
        result = ae.execute(action_name, parameters, context)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/action-space/plan")
async def action_space_plan(request: Request):
    """Generate an action plan from a goal."""
    try:
        from sparkai.agent.agent_action_space import ActionSpaceEngine
        body = await request.json()
        goal = body.get("goal", "")
        max_steps = body.get("max_steps", 10)
        context = body.get("context", {})
        ae = ActionSpaceEngine.get_instance()
        if not ae._initialized:
            ae.initialize()
        result = ae.plan_actions(goal, max_steps, context)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/action-space/history")
async def action_space_history(limit: int = Query(default=20, le=100)):
    """Get recent action execution history."""
    try:
        from sparkai.agent.agent_action_space import ActionSpaceEngine
        ae = ActionSpaceEngine.get_instance()
        if not ae._initialized:
            ae.initialize()
        history = ae.get_execution_history(limit=limit)
        return JSONResponse({"status": "success", "data": history})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Self-Reflection Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/self-reflection/status")
async def self_reflection_status():
    """Get the current status of the Self-Reflection Engine."""
    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        return JSONResponse({"status": "success", "data": sr.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/self-reflection/start-session")
async def self_reflection_start_session(request: Request):
    """Start a new reflection session."""
    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        body = await request.json()
        goal = body.get("goal", "Self-improvement session")
        context = body.get("context", {})
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        result = sr.start_session(goal, context)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/self-reflection/record-trace")
async def self_reflection_record_trace(request: Request):
    """Record a performance trace for a session."""
    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        body = await request.json()
        session_id = body.get("session_id", "")
        trace_data = body.get("trace", {})
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        result = sr.record_trace(session_id, trace_data)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/self-reflection/reflect")
async def self_reflection_reflect(request: Request):
    """Perform reflection on collected traces."""
    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        body = await request.json()
        session_id = body.get("session_id", "")
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        result = sr.reflect(session_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/self-reflection/adapt")
async def self_reflection_adapt(request: Request):
    """Generate and apply improvement strategies."""
    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        body = await request.json()
        session_id = body.get("session_id", "")
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        result = sr.adapt(session_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/self-reflection/sessions")
async def self_reflection_sessions():
    """List all reflection sessions."""
    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        sessions = sr.list_sessions()
        return JSONResponse({"status": "success", "data": sessions})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/self-reflection/insights")
async def self_reflection_insights():
    """Get global insights across all sessions."""
    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        insights = sr.get_global_insights()
        return JSONResponse({"status": "success", "data": insights})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Reasoning Chain Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reasoning-chain/status")
async def reasoning_chain_status():
    """Get the current status of the Reasoning Chain Engine."""
    try:
        from sparkai.agent.agent_reasoning_chain import ReasoningChainEngine
        rc = ReasoningChainEngine.get_instance()
        if not rc._initialized:
            rc.initialize()
        return JSONResponse({"status": "success", "data": rc.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/reasoning-chain/reason")
async def reasoning_chain_reason(request: Request):
    """Execute a reasoning chain to solve a problem."""
    try:
        from sparkai.agent.agent_reasoning_chain import ReasoningChainEngine, ReasoningMode
        body = await request.json()
        problem = body.get("problem", "")
        mode_str = body.get("mode", "deductive")
        max_steps = body.get("max_steps", 5)
        context = body.get("context", {})
        initial_beliefs = body.get("initial_beliefs", None)
        try:
            mode = ReasoningMode(mode_str)
        except ValueError:
            mode = ReasoningMode.DEDUCTIVE
        rc = ReasoningChainEngine.get_instance()
        if not rc._initialized:
            rc.initialize()
        result = rc.reason(problem, mode, max_steps, context, initial_beliefs)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/reasoning-chain/chains")
async def reasoning_chain_list():
    """List all reasoning chains."""
    try:
        from sparkai.agent.agent_reasoning_chain import ReasoningChainEngine
        rc = ReasoningChainEngine.get_instance()
        if not rc._initialized:
            rc.initialize()
        chains = rc.list_chains()
        return JSONResponse({"status": "success", "data": [c.to_dict() for c in chains]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/reasoning-chain/{chain_id}")
async def reasoning_chain_get(chain_id: str):
    """Get a specific reasoning chain by ID."""
    try:
        from sparkai.agent.agent_reasoning_chain import ReasoningChainEngine
        rc = ReasoningChainEngine.get_instance()
        if not rc._initialized:
            rc.initialize()
        chain = rc.get_chain(chain_id)
        if not chain:
            return JSONResponse({"status": "error", "message": "Chain not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": chain.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/reasoning-chain/beliefs")
async def reasoning_chain_beliefs():
    """List all belief states."""
    try:
        from sparkai.agent.agent_reasoning_chain import ReasoningChainEngine
        rc = ReasoningChainEngine.get_instance()
        if not rc._initialized:
            rc.initialize()
        beliefs = rc.list_beliefs()
        return JSONResponse({"status": "success", "data": [b.to_dict() for b in beliefs]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Task Decomposer Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/task-decomposer/status")
async def task_decomposer_status():
    """Get the current status of the Task Decomposer Engine."""
    try:
        from sparkai.agent.agent_task_decomposer import TaskDecomposerEngine
        td = TaskDecomposerEngine.get_instance()
        if not td._initialized:
            td.initialize()
        return JSONResponse({"status": "success", "data": td.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/task-decomposer/decompose")
async def task_decomposer_decompose(request: Request):
    """Decompose a goal into a task tree."""
    try:
        from sparkai.agent.agent_task_decomposer import TaskDecomposerEngine, DecompositionStrategy
        body = await request.json()
        goal = body.get("goal", "")
        strategy_str = body.get("strategy", "hybrid")
        max_depth = body.get("max_depth", 4)
        context = body.get("context", {})
        template = body.get("template", None)
        try:
            strategy = DecompositionStrategy(strategy_str)
        except ValueError:
            strategy = DecompositionStrategy.HYBRID
        td = TaskDecomposerEngine.get_instance()
        if not td._initialized:
            td.initialize()
        result = td.decompose(goal, strategy, max_depth, context, template)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/task-decomposer/plans")
async def task_decomposer_plans():
    """List all execution plans."""
    try:
        from sparkai.agent.agent_task_decomposer import TaskDecomposerEngine
        td = TaskDecomposerEngine.get_instance()
        if not td._initialized:
            td.initialize()
        plans = td.list_plans()
        return JSONResponse({"status": "success", "data": [p.to_dict() for p in plans]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/task-decomposer/plan/{plan_id}")
async def task_decomposer_get_plan(plan_id: str):
    """Get a specific execution plan."""
    try:
        from sparkai.agent.agent_task_decomposer import TaskDecomposerEngine
        td = TaskDecomposerEngine.get_instance()
        if not td._initialized:
            td.initialize()
        plan = td.get_plan(plan_id)
        if not plan:
            return JSONResponse({"status": "error", "message": "Plan not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": plan.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/task-decomposer/execute-plan")
async def task_decomposer_execute(request: Request):
    """Execute a plan's tasks."""
    try:
        from sparkai.agent.agent_task_decomposer import TaskDecomposerEngine
        body = await request.json()
        plan_id = body.get("plan_id", "")
        td = TaskDecomposerEngine.get_instance()
        if not td._initialized:
            td.initialize()
        result = td.execute_plan(plan_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Perception Pipeline Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/perception/status")
async def perception_status():
    """Get the current status of the Perception Pipeline."""
    try:
        from sparkai.agent.agent_perception_pipeline import PerceptionPipeline
        pp = PerceptionPipeline.get_instance()
        if not pp._initialized:
            pp.initialize()
        return JSONResponse({"status": "success", "data": pp.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/perception/perceive")
async def perception_perceive(request: Request):
    """Generate a perception snapshot for an agent."""
    try:
        from sparkai.agent.agent_perception_pipeline import PerceptionPipeline, PerceptionChannel
        body = await request.json()
        agent_id = body.get("agent_id", "")
        world_state = body.get("world_state", {})
        channels_str = body.get("channels", None)
        agent_position = body.get("agent_position", None)
        max_percepts = body.get("max_percepts", 20)
        channels = None
        if channels_str:
            try:
                channels = [PerceptionChannel(c) for c in channels_str]
            except ValueError:
                pass
        pp = PerceptionPipeline.get_instance()
        if not pp._initialized:
            pp.initialize()
        result = pp.perceive(agent_id, world_state, channels, agent_position, max_percepts)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/perception/snapshots/{agent_id}")
async def perception_snapshots(agent_id: str):
    """Get perception snapshots for an agent."""
    try:
        from sparkai.agent.agent_perception_pipeline import PerceptionPipeline
        pp = PerceptionPipeline.get_instance()
        if not pp._initialized:
            pp.initialize()
        snapshots = pp.get_snapshots(agent_id)
        return JSONResponse({"status": "success", "data": [s.to_dict() for s in snapshots]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Engine Event Bus Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/event-bus/status")
async def event_bus_status():
    """Get the current status of the Engine Event Bus."""
    try:
        from sparkai.engine.engine_event_bus import EngineEventBus
        eb = EngineEventBus.get_instance()
        if not eb._initialized:
            eb.initialize()
        return JSONResponse({"status": "success", "data": eb.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/event-bus/publish")
async def event_bus_publish(request: Request):
    """Publish an event to the bus."""
    try:
        from sparkai.engine.engine_event_bus import EngineEventBus, EngineEvent, EventCategory, EventDeliveryMode
        body = await request.json()
        event_type = body.get("event_type", "custom_event")
        category_str = body.get("category", "custom")
        source = body.get("source", "api")
        data = body.get("data", {})
        tags = body.get("tags", [])
        try:
            category = EventCategory(category_str)
        except ValueError:
            category = EventCategory.CUSTOM
        event = EngineEvent(
            event_type=event_type,
            category=category,
            source=source,
            data=data,
            tags=tags,
        )
        eb = EngineEventBus.get_instance()
        if not eb._initialized:
            eb.initialize()
        result = eb.publish(event, EventDeliveryMode.ASYNCHRONOUS)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/event-bus/agent-to-engine")
async def event_bus_agent_to_engine(request: Request):
    """Route an agent event to the engine layer."""
    try:
        from sparkai.engine.engine_event_bus import EngineEventBus
        body = await request.json()
        eb = EngineEventBus.get_instance()
        if not eb._initialized:
            eb.initialize()
        result = eb.route_agent_to_engine(body)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/event-bus/engine-to-agent")
async def event_bus_engine_to_agent(request: Request):
    """Route an engine event to the agent layer."""
    try:
        from sparkai.engine.engine_event_bus import EngineEventBus
        body = await request.json()
        eb = EngineEventBus.get_instance()
        if not eb._initialized:
            eb.initialize()
        result = eb.route_engine_to_agent(body)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/event-bus/channels")
async def event_bus_channels():
    """List all event channels."""
    try:
        from sparkai.engine.engine_event_bus import EngineEventBus
        eb = EngineEventBus.get_instance()
        if not eb._initialized:
            eb.initialize()
        channels = eb.list_channels()
        return JSONResponse({"status": "success", "data": channels})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/event-bus/history")
async def event_bus_history(limit: int = Query(default=50, le=200)):
    """Get recent event history."""
    try:
        from sparkai.engine.engine_event_bus import EngineEventBus
        eb = EngineEventBus.get_instance()
        if not eb._initialized:
            eb.initialize()
        history = eb.get_event_history()[-limit:]
        return JSONResponse({"status": "success", "data": history})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Tile Map Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tilemap/status")
async def tilemap_status():
    """Get the current status of the Tile Map Engine."""
    try:
        from sparkai.engine.engine_tile_map import TileMapEngine
        tm = TileMapEngine.get_instance()
        if not tm._initialized:
            tm.initialize()
        return JSONResponse({"status": "success", "data": tm.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/tilemap/create")
async def tilemap_create(request: Request):
    """Create a new tile map."""
    try:
        from sparkai.engine.engine_tile_map import TileMapEngine
        body = await request.json()
        map_name = body.get("name", f"Map-{int(time.time())}")
        width = body.get("width", 50)
        height = body.get("height", 50)
        tile_size = body.get("tile_size", 32)
        tm = TileMapEngine.get_instance()
        if not tm._initialized:
            tm.initialize()
        result = tm.create_map(map_name, width, height, tile_size)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/tilemap/generate")
async def tilemap_generate(request: Request):
    """Generate a tile map procedurally."""
    try:
        from sparkai.engine.engine_tile_map import TileMapEngine, GenerationAlgorithm
        body = await request.json()
        map_name = body.get("map_name", "")
        algorithm_str = body.get("algorithm", "perlin")
        config = body.get("config", {})
        try:
            algorithm = GenerationAlgorithm(algorithm_str)
        except ValueError:
            algorithm = GenerationAlgorithm.PERLIN
        tm = TileMapEngine.get_instance()
        if not tm._initialized:
            tm.initialize()
        result = tm.generate_map(map_name, algorithm, config)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/tilemap/add-layer")
async def tilemap_add_layer(request: Request):
    """Add a layer to a tile map."""
    try:
        from sparkai.engine.engine_tile_map import TileMapEngine, TileLayerType
        body = await request.json()
        map_name = body.get("map_name", "")
        layer_name = body.get("layer_name", f"Layer-{int(time.time())}")
        layer_type_str = body.get("layer_type", "tile")
        z_index = body.get("z_index", 0)
        try:
            layer_type = TileLayerType(layer_type_str)
        except ValueError:
            layer_type = TileLayerType.TILE
        tm = TileMapEngine.get_instance()
        if not tm._initialized:
            tm.initialize()
        result = tm.add_layer(map_name, layer_name, layer_type, z_index)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/tilemap/paint")
async def tilemap_paint(request: Request):
    """Paint tiles on a layer."""
    try:
        from sparkai.engine.engine_tile_map import TileMapEngine
        body = await request.json()
        map_name = body.get("map_name", "")
        layer_name = body.get("layer_name", "")
        tiles = body.get("tiles", [])
        tm = TileMapEngine.get_instance()
        if not tm._initialized:
            tm.initialize()
        result = tm.paint_tiles(map_name, layer_name, tiles)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/tilemap/maps")
async def tilemap_list():
    """List all tile maps."""
    try:
        from sparkai.engine.engine_tile_map import TileMapEngine
        tm = TileMapEngine.get_instance()
        if not tm._initialized:
            tm.initialize()
        maps = tm.list_maps()
        return JSONResponse({"status": "success", "data": [m.to_dict() for m in maps]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/tilemap/{map_name}")
async def tilemap_get(map_name: str):
    """Get a specific tile map."""
    try:
        from sparkai.engine.engine_tile_map import TileMapEngine
        tm = TileMapEngine.get_instance()
        if not tm._initialized:
            tm.initialize()
        tilemap = tm.get_map(map_name)
        if not tilemap:
            return JSONResponse({"status": "error", "message": "Map not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": tilemap.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Prefab System Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/prefab/status")
async def prefab_status():
    """Get the current status of the Prefab System."""
    try:
        from sparkai.engine.engine_prefab import PrefabSystem
        ps = PrefabSystem.get_instance()
        if not ps._initialized:
            ps.initialize()
        return JSONResponse({"status": "success", "data": ps.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/prefab/create")
async def prefab_create(request: Request):
    """Create a new prefab definition."""
    try:
        from sparkai.engine.engine_prefab import PrefabSystem, PrefabCategory
        body = await request.json()
        name = body.get("name", f"Prefab-{int(time.time())}")
        category_str = body.get("category", "custom")
        properties = body.get("properties", {})
        components = body.get("components", [])
        try:
            category = PrefabCategory(category_str)
        except ValueError:
            category = PrefabCategory.CUSTOM
        ps = PrefabSystem.get_instance()
        if not ps._initialized:
            ps.initialize()
        result = ps.create_prefab(name, category, properties, components)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/prefab/instantiate")
async def prefab_instantiate(request: Request):
    """Instantiate a prefab."""
    try:
        from sparkai.engine.engine_prefab import PrefabSystem
        body = await request.json()
        prefab_name = body.get("prefab_name", "")
        position = tuple(body.get("position", [0, 0, 0]))
        rotation = tuple(body.get("rotation", [0, 0, 0]))
        scale = tuple(body.get("scale", [1, 1, 1]))
        overrides = body.get("overrides", None)
        scene_id = body.get("scene_id", None)
        ps = PrefabSystem.get_instance()
        if not ps._initialized:
            ps.initialize()
        result = ps.instantiate(prefab_name, position, rotation, scale, overrides, scene_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/prefab/generate")
async def prefab_generate(request: Request):
    """Generate prefabs from a description."""
    try:
        from sparkai.engine.engine_prefab import PrefabSystem
        body = await request.json()
        description = body.get("description", "")
        count = body.get("count", 5)
        ps = PrefabSystem.get_instance()
        if not ps._initialized:
            ps.initialize()
        result = ps.generate_prefabs(description, count)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/prefab/prefabs")
async def prefab_list():
    """List all prefabs."""
    try:
        from sparkai.engine.engine_prefab import PrefabSystem
        ps = PrefabSystem.get_instance()
        if not ps._initialized:
            ps.initialize()
        prefabs = ps.list_prefabs()
        return JSONResponse({"status": "success", "data": [p.to_dict() for p in prefabs]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/prefab/instances")
async def prefab_instances():
    """List all prefab instances."""
    try:
        from sparkai.engine.engine_prefab import PrefabSystem
        ps = PrefabSystem.get_instance()
        if not ps._initialized:
            ps.initialize()
        instances = ps.list_instances()
        return JSONResponse({"status": "success", "data": [i.to_dict() for i in instances]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Input Action System Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/input-action/status")
async def input_action_status():
    """Get the current status of the Input Action System."""
    try:
        from sparkai.engine.engine_input_action import InputActionSystem
        ias = InputActionSystem.get_instance()
        if not ias._initialized:
            ias.initialize()
        return JSONResponse({"status": "success", "data": ias.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/input-action/register")
async def input_action_register(request: Request):
    """Register a new input action."""
    try:
        from sparkai.engine.engine_input_action import InputActionSystem, InputAction, InputTrigger, InputDeviceType, InputTriggerType
        body = await request.json()
        name = body.get("name", f"Action-{int(time.time())}")
        triggers_data = body.get("triggers", [])
        description = body.get("description", "")
        triggers = []
        for t in triggers_data:
            try:
                device = InputDeviceType(t.get("device", "keyboard"))
                trigger_type = InputTriggerType(t.get("trigger_type", "press"))
            except ValueError:
                device = InputDeviceType.KEYBOARD
                trigger_type = InputTriggerType.PRESS
            triggers.append(InputTrigger(
                device=device,
                key=t.get("key", ""),
                trigger_type=trigger_type,
                modifiers=t.get("modifiers", []),
            ))
        action = InputAction(name=name, description=description, triggers=triggers)
        ias = InputActionSystem.get_instance()
        if not ias._initialized:
            ias.initialize()
        result = ias.register_action(action)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/input-action/process")
async def input_action_process(request: Request):
    """Process a raw input event."""
    try:
        from sparkai.engine.engine_input_action import InputActionSystem, InputDeviceType, InputTriggerType
        body = await request.json()
        device_str = body.get("device", "keyboard")
        key = body.get("key", "")
        value = body.get("value", 1.0)
        trigger_type_str = body.get("trigger_type", "press")
        modifiers = body.get("modifiers", [])
        try:
            device = InputDeviceType(device_str)
        except ValueError:
            device = InputDeviceType.KEYBOARD
        try:
            trigger_type = InputTriggerType(trigger_type_str)
        except ValueError:
            trigger_type = InputTriggerType.PRESS
        ias = InputActionSystem.get_instance()
        if not ias._initialized:
            ias.initialize()
        result = ias.process_input(device, key, value, trigger_type, modifiers)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/input-action/generate-scheme")
async def input_action_generate_scheme(request: Request):
    """Generate a control scheme for a game genre."""
    try:
        from sparkai.engine.engine_input_action import InputActionSystem
        body = await request.json()
        game_genre = body.get("game_genre", "platformer")
        description = body.get("description", "")
        ias = InputActionSystem.get_instance()
        if not ias._initialized:
            ias.initialize()
        result = ias.generate_scheme(game_genre, description)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/input-action/actions")
async def input_action_list():
    """List all input actions."""
    try:
        from sparkai.engine.engine_input_action import InputActionSystem
        ias = InputActionSystem.get_instance()
        if not ias._initialized:
            ias.initialize()
        actions = ias.list_actions()
        return JSONResponse({"status": "success", "data": [a.to_dict() for a in actions]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Shader Material System Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/shader-material/status")
async def shader_material_status():
    """Get the current status of the Shader Material System."""
    try:
        from sparkai.engine.engine_shader_material import ShaderMaterialSystem
        sms = ShaderMaterialSystem.get_instance()
        if not sms._initialized:
            sms.initialize()
        return JSONResponse({"status": "success", "data": sms.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/shader-material/create")
async def shader_material_create(request: Request):
    """Create a new material."""
    try:
        from sparkai.engine.engine_shader_material import ShaderMaterialSystem
        body = await request.json()
        name = body.get("name", f"Material-{int(time.time())}")
        config = body.get("config", {})
        sms = ShaderMaterialSystem.get_instance()
        if not sms._initialized:
            sms.initialize()
        result = sms.create_material(name, config)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/shader-material/generate")
async def shader_material_generate(request: Request):
    """Generate a shader material from a description."""
    try:
        from sparkai.engine.engine_shader_material import ShaderMaterialSystem
        body = await request.json()
        description = body.get("description", "")
        sms = ShaderMaterialSystem.get_instance()
        if not sms._initialized:
            sms.initialize()
        result = sms.generate_shader(description)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/shader-material/apply")
async def shader_material_apply(request: Request):
    """Apply a material to an entity."""
    try:
        from sparkai.engine.engine_shader_material import ShaderMaterialSystem
        body = await request.json()
        entity_id = body.get("entity_id", "")
        material_name = body.get("material_name", "")
        sms = ShaderMaterialSystem.get_instance()
        if not sms._initialized:
            sms.initialize()
        result = sms.apply_material(entity_id, material_name)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/shader-material/materials")
async def shader_material_list():
    """List all materials."""
    try:
        from sparkai.engine.engine_shader_material import ShaderMaterialSystem
        sms = ShaderMaterialSystem.get_instance()
        if not sms._initialized:
            sms.initialize()
        materials = sms.list_materials()
        return JSONResponse({"status": "success", "data": [m.to_dict() for m in materials]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/shader-material/shaders")
async def shader_material_shaders():
    """List all shader programs."""
    try:
        from sparkai.engine.engine_shader_material import ShaderMaterialSystem
        sms = ShaderMaterialSystem.get_instance()
        if not sms._initialized:
            sms.initialize()
        shaders = sms.list_shaders()
        return JSONResponse({"status": "success", "data": [s.to_dict() for s in shaders]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Decision Graph Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/decision-graph/status")
async def decision_graph_status():
    """Get the current status of the Decision Graph Engine."""
    try:
        from sparkai.agent.agent_decision_graph import DecisionGraphEngine
        dg = DecisionGraphEngine.get_instance()
        if not dg._initialized:
            dg.initialize()
        return JSONResponse({"status": "success", "data": dg.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/decision-graph/graphs")
async def decision_graph_list():
    """List all decision graphs."""
    try:
        from sparkai.agent.agent_decision_graph import DecisionGraphEngine
        dg = DecisionGraphEngine.get_instance()
        if not dg._initialized:
            dg.initialize()
        graphs = dg.list_graphs()
        return JSONResponse({"status": "success", "data": [g.to_dict() for g in graphs]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/decision-graph/create")
async def decision_graph_create(request: Request):
    """Create a new decision graph."""
    try:
        from sparkai.agent.agent_decision_graph import DecisionGraphEngine, DecisionNodeType, DecisionNode
        body = await request.json()
        name = body.get("name", f"Graph-{int(time.time())}")
        root_type_str = body.get("root_type", "selector")
        description = body.get("description", "")
        graph_data = body.get("graph_data", {})
        try:
            root_type = DecisionNodeType(root_type_str)
        except ValueError:
            root_type = DecisionNodeType.SELECTOR
        dg = DecisionGraphEngine.get_instance()
        if not dg._initialized:
            dg.initialize()
        graph = dg.create_graph(name, root_type, description)
        # Add nodes and edges from graph_data if provided
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        for node_data in nodes:
            try:
                node_type = DecisionNodeType(node_data.get("node_type", "condition"))
            except ValueError:
                node_type = DecisionNodeType.CONDITION
            node = DecisionNode(
                node_id=node_data.get("node_id", ""),
                node_type=node_type,
                name=node_data.get("name", ""),
                condition=node_data.get("condition"),
                action=node_data.get("action"),
                action_params=node_data.get("action_params", {}),
                priority=node_data.get("priority", 0),
                probability=node_data.get("probability", 1.0),
            )
            dg.add_node(graph.graph_id, node)
        for edge_data in edges:
            dg.add_edge(
                graph.graph_id,
                edge_data.get("source_id", ""),
                edge_data.get("target_id", ""),
                weight=edge_data.get("weight", 1.0),
                condition=edge_data.get("condition"),
                label=edge_data.get("label", ""),
            )
        return JSONResponse({"status": "success", "data": graph.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/decision-graph/evaluate")
async def decision_graph_evaluate(request: Request):
    """Evaluate a decision graph with context."""
    try:
        from sparkai.agent.agent_decision_graph import DecisionGraphEngine
        body = await request.json()
        graph_id = body.get("graph_id", "")
        context = body.get("context", {})
        dg = DecisionGraphEngine.get_instance()
        if not dg._initialized:
            dg.initialize()
        result = dg.evaluate(graph_id, context)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Context Hypergraph Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/context-hypergraph/status")
async def context_hypergraph_status():
    """Get the current status of the Context Hypergraph Engine."""
    try:
        from sparkai.agent.agent_context_hypergraph import ContextHypergraphEngine
        ch = ContextHypergraphEngine.get_instance()
        if not ch._initialized:
            ch.initialize()
        return JSONResponse({"status": "success", "data": ch.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/context-hypergraph/nodes")
async def context_hypergraph_nodes():
    """List all context hypergraph nodes."""
    try:
        from sparkai.agent.agent_context_hypergraph import ContextHypergraphEngine
        ch = ContextHypergraphEngine.get_instance()
        if not ch._initialized:
            ch.initialize()
        nodes = ch.list_nodes()
        return JSONResponse({"status": "success", "data": [n.to_dict() for n in nodes]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/context-hypergraph/query")
async def context_hypergraph_query(request: Request):
    """Query a context subgraph."""
    try:
        from sparkai.agent.agent_context_hypergraph import ContextHypergraphEngine
        body = await request.json()
        query = body.get("query", "")
        ch = ContextHypergraphEngine.get_instance()
        if not ch._initialized:
            ch.initialize()
        result = ch.query(query)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Resource Streaming Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/resource-streaming/status")
async def resource_streaming_status():
    """Get the current status of the Resource Streaming Engine."""
    try:
        from sparkai.engine.engine_resource_streaming import ResourceStreamingEngine
        rs = ResourceStreamingEngine.get_instance()
        if not rs._initialized:
            rs.initialize()
        return JSONResponse({"status": "success", "data": rs.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/resource-streaming/zones")
async def resource_streaming_zones():
    """List all streaming zones."""
    try:
        from sparkai.engine.engine_resource_streaming import ResourceStreamingEngine
        rs = ResourceStreamingEngine.get_instance()
        if not rs._initialized:
            rs.initialize()
        zones = rs.list_zones()
        return JSONResponse({"status": "success", "data": [z.to_dict() for z in zones]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/resource-streaming/create-zone")
async def resource_streaming_create_zone(request: Request):
    """Create a new streaming zone."""
    try:
        from sparkai.engine.engine_resource_streaming import ResourceStreamingEngine
        body = await request.json()
        zone_name = body.get("zone_name", f"Zone-{int(time.time())}")
        priority = body.get("priority", 1)
        rs = ResourceStreamingEngine.get_instance()
        if not rs._initialized:
            rs.initialize()
        result = rs.create_zone(zone_name, priority)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# State Reconciliation Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/state-reconciliation/status")
async def state_reconciliation_status():
    """Get the current status of the State Reconciliation Engine."""
    try:
        from sparkai.engine.engine_state_reconciliation import StateReconciliationEngine
        src = StateReconciliationEngine.get_instance()
        if not src._initialized:
            src.initialize()
        return JSONResponse({"status": "success", "data": src.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/state-reconciliation/history")
async def state_reconciliation_history():
    """List reconciliation history."""
    try:
        from sparkai.engine.engine_state_reconciliation import StateReconciliationEngine
        src = StateReconciliationEngine.get_instance()
        if not src._initialized:
            src.initialize()
        history = src.get_history()
        return JSONResponse({"status": "success", "data": [h.to_dict() for h in history]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/state-reconciliation/reconcile")
async def state_reconciliation_reconcile(request: Request):
    """Reconcile two states."""
    try:
        from sparkai.engine.engine_state_reconciliation import StateReconciliationEngine
        body = await request.json()
        state_a = body.get("state_a", {})
        state_b = body.get("state_b", {})
        src = StateReconciliationEngine.get_instance()
        if not src._initialized:
            src.initialize()
        result = src.reconcile(state_a, state_b)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Unified Hub Status (aggregated view of all systems)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/unified/status")
async def unified_status():
    """Get aggregated status of all agent and engine systems."""
    systems_status = {}
    try:
        from sparkai.agent.agent_gateway import AgentGateway
        gw = AgentGateway.get_instance()
        if not gw._initialized:
            gw.initialize()
        systems_status["gateway"] = gw.get_status()
    except Exception:
        systems_status["gateway"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_timeline import TimelineManager
        tm = TimelineManager.get_instance()
        if not tm._initialized:
            tm.initialize()
        systems_status["timeline"] = tm.get_status()
    except Exception:
        systems_status["timeline"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_god_mode import GodModeController
        gm = GodModeController.get_instance()
        if not gm._is_initialized:
            gm.initialize()
        systems_status["god_mode"] = gm.get_status()
    except Exception:
        systems_status["god_mode"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_event_bus import EngineEventBus
        eb = EngineEventBus.get_instance()
        if not eb._initialized:
            eb.initialize()
        systems_status["event_bus"] = eb.get_status()
    except Exception:
        systems_status["event_bus"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_tile_map import TileMapEngine
        tme = TileMapEngine.get_instance()
        if not tme._initialized:
            tme.initialize()
        systems_status["tilemap"] = tme.get_status()
    except Exception:
        systems_status["tilemap"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_prefab import PrefabSystem
        ps = PrefabSystem.get_instance()
        if not ps._initialized:
            ps.initialize()
        systems_status["prefab"] = ps.get_status()
    except Exception:
        systems_status["prefab"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_input_action import InputActionSystem
        ias = InputActionSystem.get_instance()
        if not ias._initialized:
            ias.initialize()
        systems_status["input_action"] = ias.get_status()
    except Exception:
        systems_status["input_action"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_shader_material import ShaderMaterialSystem
        sms = ShaderMaterialSystem.get_instance()
        if not sms._initialized:
            sms.initialize()
        systems_status["shader_material"] = sms.get_status()
    except Exception:
        systems_status["shader_material"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_action_space import ActionSpaceEngine
        ae = ActionSpaceEngine.get_instance()
        if not ae._initialized:
            ae.initialize()
        systems_status["action_space"] = ae.get_status()
    except Exception:
        systems_status["action_space"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_self_reflection import SelfReflectionEngine
        sr = SelfReflectionEngine.get_instance()
        if not sr._initialized:
            sr.initialize()
        systems_status["self_reflection"] = sr.get_status()
    except Exception:
        systems_status["self_reflection"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_reasoning_chain import ReasoningChainEngine
        rc = ReasoningChainEngine.get_instance()
        if not rc._initialized:
            rc.initialize()
        systems_status["reasoning_chain"] = rc.get_status()
    except Exception:
        systems_status["reasoning_chain"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_task_decomposer import TaskDecomposerEngine
        td = TaskDecomposerEngine.get_instance()
        if not td._initialized:
            td.initialize()
        systems_status["task_decomposer"] = td.get_status()
    except Exception:
        systems_status["task_decomposer"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_perception_pipeline import PerceptionPipeline
        pp = PerceptionPipeline.get_instance()
        if not pp._initialized:
            pp.initialize()
        systems_status["perception"] = pp.get_status()
    except Exception:
        systems_status["perception"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        systems_status["ai_native_brain"] = brain.get_status()
    except Exception:
        systems_status["ai_native_brain"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        systems_status["ai_native_runtime"] = runtime.get_status()
    except Exception:
        systems_status["ai_native_runtime"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge
        bridge = AgentEngineBridge.get_instance()
        if not bridge._initialized:
            bridge.initialize()
        systems_status["agent_engine_bridge"] = bridge.get_status()
    except Exception:
        systems_status["agent_engine_bridge"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_tool_orchestrator import AgentToolOrchestrator
        to = AgentToolOrchestrator.get_instance()
        if not to._initialized:
            to.initialize()
        systems_status["tool_orchestrator"] = to.get_status()
    except Exception:
        systems_status["tool_orchestrator"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_world_synthesizer import AgentWorldSynthesizer
        ws = AgentWorldSynthesizer.get_instance()
        if not ws._initialized:
            ws.initialize()
        systems_status["world_synthesizer"] = ws.get_status()
    except Exception:
        systems_status["world_synthesizer"] = {"status": "unavailable"}

    try:
        from sparkai.agent.agent_semantic_planner import AgentSemanticPlanner
        sp = AgentSemanticPlanner.get_instance()
        if not sp._initialized:
            sp.initialize()
        systems_status["semantic_planner"] = sp.get_status()
    except Exception:
        systems_status["semantic_planner"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        systems_status["visual_scripting"] = vs.get_status()
    except Exception:
        systems_status["visual_scripting"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        systems_status["cross_platform_builder"] = cb.get_status()
    except Exception:
        systems_status["cross_platform_builder"] = {"status": "unavailable"}

    try:
        from sparkai.engine.engine_procedural_animation import EngineProceduralAnimation
        pa = EngineProceduralAnimation.get_instance()
        if not pa._initialized:
            pa.initialize()
        systems_status["procedural_animation"] = pa.get_status()
    except Exception:
        systems_status["procedural_animation"] = {"status": "unavailable"}

    active_count = sum(1 for s in systems_status.values() if s.get("initialized", False))
    total_count = len(systems_status)

    return JSONResponse({
        "status": "success",
        "data": {
            "systems": systems_status,
            "active_systems": active_count,
            "total_systems": total_count,
            "timestamp": time.time(),
        }
    })


@router.post("/unified/initialize-all")
async def unified_initialize_all():
    """Initialize all agent and engine systems."""
    results = {}

    init_order = [
        ("gateway", "sparkai.agent.agent_gateway", "AgentGateway"),
        ("timeline", "sparkai.agent.agent_timeline", "TimelineManager"),
        ("god_mode", "sparkai.agent.agent_god_mode", "GodModeController"),
        ("event_bus", "sparkai.engine.engine_event_bus", "EngineEventBus"),
        ("tilemap", "sparkai.engine.engine_tile_map", "TileMapEngine"),
        ("prefab", "sparkai.engine.engine_prefab", "PrefabSystem"),
        ("input_action", "sparkai.engine.engine_input_action", "InputActionSystem"),
        ("shader_material", "sparkai.engine.engine_shader_material", "ShaderMaterialSystem"),
        ("action_space", "sparkai.agent.agent_action_space", "ActionSpaceEngine"),
        ("self_reflection", "sparkai.agent.agent_self_reflection", "SelfReflectionEngine"),
        ("reasoning_chain", "sparkai.agent.agent_reasoning_chain", "ReasoningChainEngine"),
        ("task_decomposer", "sparkai.agent.agent_task_decomposer", "TaskDecomposerEngine"),
        ("perception", "sparkai.agent.agent_perception_pipeline", "PerceptionPipeline"),
        ("ai_native_brain", "sparkai.agent.agent_ai_native_brain", "AINativeBrain"),
        ("ai_native_runtime", "sparkai.engine.engine_ai_native_runtime", "AINativeGameRuntime"),
        ("agent_engine_bridge", "sparkai.engine.engine_agent_bridge", "AgentEngineBridge"),
        ("tool_orchestrator", "sparkai.agent.agent_tool_orchestrator", "AgentToolOrchestrator"),
        ("world_synthesizer", "sparkai.agent.agent_world_synthesizer", "AgentWorldSynthesizer"),
        ("semantic_planner", "sparkai.agent.agent_semantic_planner", "AgentSemanticPlanner"),
        ("visual_scripting", "sparkai.engine.engine_visual_scripting", "EngineVisualScripting"),
        ("cross_platform_builder", "sparkai.engine.engine_cross_platform_builder", "EngineCrossPlatformBuilder"),
        ("procedural_animation", "sparkai.engine.engine_procedural_animation", "EngineProceduralAnimation"),
    ]

    for name, module_path, class_name in init_order:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            instance = cls.get_instance()
            if not instance._initialized:
                instance.initialize()
            results[name] = {"status": "ok", "initialized": True}
        except Exception as e:
            results[name] = {"status": "error", "message": str(e)}

    return JSONResponse({"status": "success", "data": results})


# ═══════════════════════════════════════════════════════════════════════════════
# AI-Native Cognitive Brain Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ai-native-brain/status")
async def ai_native_brain_status():
    """Get the current status of the AI-Native Cognitive Brain."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        return JSONResponse({"status": "success", "data": brain.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-brain/snapshot")
async def ai_native_brain_snapshot():
    """Get a snapshot of the brain's current state."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        snapshot = brain.get_snapshot()
        return JSONResponse({"status": "success", "data": snapshot.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/reason")
async def ai_native_brain_reason(request: Request):
    """Execute a reasoning chain on a query."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        body = await request.json()
        query = body.get("query", "")
        context = body.get("context", {})
        max_steps = body.get("max_steps", 5)
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        result = brain.reason(query, context, max_steps=max_steps)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/plan")
async def ai_native_brain_plan(request: Request):
    """Generate an action plan from a goal."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        body = await request.json()
        goal = body.get("goal", "")
        context = body.get("context", {})
        max_actions = body.get("max_actions", 10)
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        result = brain.plan(goal, context, max_actions=max_actions)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/execute-plan")
async def ai_native_brain_execute_plan(request: Request):
    """Execute all actions in a plan."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        body = await request.json()
        plan_id = body.get("plan_id", "")
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        results = brain.execute_plan(plan_id)
        return JSONResponse({"status": "success", "data": results})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/memory/store")
async def ai_native_brain_store_memory(request: Request):
    """Store a memory entry in the brain."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        body = await request.json()
        content = body.get("content", {})
        importance = body.get("importance", 0.5)
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        entry_id = brain.store_memory(content, importance=importance)
        return JSONResponse({"status": "success", "data": {"entry_id": entry_id}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/memory/recall")
async def ai_native_brain_recall_memory(request: Request):
    """Recall memories matching a query."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        body = await request.json()
        query = body.get("query", "")
        max_results = body.get("max_results", 10)
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        results = brain.recall_memory(query, max_results=max_results)
        return JSONResponse({"status": "success", "data": [r.to_dict() for r in results]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/learn")
async def ai_native_brain_learn(request: Request):
    """Learn from an experience."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        body = await request.json()
        experience = body.get("experience", {})
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        result = brain.learn_from_experience(experience)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/reflect")
async def ai_native_brain_reflect():
    """Perform self-reflection."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        result = brain.reflect()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-brain/world-state")
async def ai_native_brain_world_state():
    """Get the current world model state."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        result = brain.get_world_state()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/predict")
async def ai_native_brain_predict(request: Request):
    """Predict future world states."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        body = await request.json()
        steps_ahead = body.get("steps_ahead", 5)
        brain = AINativeBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        result = brain.predict_world_state(steps_ahead=steps_ahead)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-brain/reset")
async def ai_native_brain_reset():
    """Reset the cognitive brain."""
    try:
        from sparkai.agent.agent_ai_native_brain import AINativeBrain
        brain = AINativeBrain.get_instance()
        brain.reset()
        return JSONResponse({"status": "success", "data": {"message": "Brain reset complete"}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# AI-Native Game Runtime Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ai-native-runtime/status")
async def ai_native_runtime_status():
    """Get the current status of the AI-Native Game Runtime."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        return JSONResponse({"status": "success", "data": runtime.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/tick")
async def ai_native_runtime_tick(request: Request):
    """Execute a single game loop tick."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        delta_time = body.get("delta_time", 0.016)
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        frame = runtime.tick(delta_time=delta_time)
        return JSONResponse({"status": "success", "data": frame.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/scene/create")
async def ai_native_runtime_create_scene(request: Request):
    """Create a new game scene."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        name = body.get("name", "New Scene")
        config = body.get("config", {})
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        scene = runtime.create_scene(name, config)
        return JSONResponse({"status": "success", "data": scene.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/scene/load")
async def ai_native_runtime_load_scene(request: Request):
    """Load a scene."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        scene_id = body.get("scene_id", "")
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        success = runtime.load_scene(scene_id)
        return JSONResponse({"status": "success", "data": {"success": success}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-runtime/scenes")
async def ai_native_runtime_list_scenes():
    """List all scenes."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        scenes = runtime.list_scenes()
        return JSONResponse({"status": "success", "data": scenes})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/entity/create")
async def ai_native_runtime_create_entity(request: Request):
    """Create a new game entity."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        name = body.get("name", "")
        components = body.get("components", {})
        tags = body.get("tags", [])
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        entity = runtime.create_entity(name=name, components=components, tags=tags)
        return JSONResponse({"status": "success", "data": entity.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/entity/destroy")
async def ai_native_runtime_destroy_entity(request: Request):
    """Destroy a game entity."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        entity_id = body.get("entity_id", "")
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        success = runtime.destroy_entity(entity_id)
        return JSONResponse({"status": "success", "data": {"success": success}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-runtime/entity/{entity_id}")
async def ai_native_runtime_get_entity(entity_id: str):
    """Get an entity by ID."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        entity = runtime.get_entity(entity_id)
        if entity:
            return JSONResponse({"status": "success", "data": entity.to_dict()})
        return JSONResponse({"status": "error", "message": "Entity not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/component/set")
async def ai_native_runtime_set_component(request: Request):
    """Set a component on an entity."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        entity_id = body.get("entity_id", "")
        component_name = body.get("component_name", "")
        data = body.get("data", {})
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        success = runtime.set_component(entity_id, component_name, data)
        return JSONResponse({"status": "success", "data": {"success": success}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/input/simulate")
async def ai_native_runtime_simulate_input(request: Request):
    """Simulate an input action."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        action = body.get("action", "")
        value = body.get("value", 1.0)
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        runtime.simulate_input(action, value)
        return JSONResponse({"status": "success", "data": {"action": action, "value": value}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-runtime/performance")
async def ai_native_runtime_performance():
    """Get performance report."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        report = runtime.get_performance_report()
        return JSONResponse({"status": "success", "data": report})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-runtime/frames")
async def ai_native_runtime_frames(count: int = 60):
    """Get recent frame data."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        frames = runtime.get_frame_history(count)
        return JSONResponse({"status": "success", "data": frames})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/save")
async def ai_native_runtime_save():
    """Save the runtime state."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        state = runtime.save_state()
        return JSONResponse({"status": "success", "data": state})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/load")
async def ai_native_runtime_load(request: Request):
    """Load a runtime state."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        body = await request.json()
        state = body.get("state", {})
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        success = runtime.load_state(state)
        return JSONResponse({"status": "success", "data": {"success": success}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-runtime/snapshot")
async def ai_native_runtime_snapshot():
    """Get a runtime snapshot."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        if not runtime._initialized:
            runtime.initialize()
        snapshot = runtime.create_snapshot()
        return JSONResponse({"status": "success", "data": snapshot.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-runtime/reset")
async def ai_native_runtime_reset():
    """Reset the game runtime."""
    try:
        from sparkai.engine.engine_ai_native_runtime import AINativeGameRuntime
        runtime = AINativeGameRuntime.get_instance()
        runtime.reset()
        return JSONResponse({"status": "success", "data": {"message": "Runtime reset complete"}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent-Engine Bridge Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/agent-engine-bridge/status")
async def agent_engine_bridge_status():
    """Get the current status of the Agent-Engine Bridge."""
    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge
        bridge = AgentEngineBridge.get_instance()
        if not bridge._initialized:
            bridge.initialize()
        return JSONResponse({"status": "success", "data": bridge.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/agent-engine-bridge/command")
async def agent_engine_bridge_command(request: Request):
    """Send a command through the bridge."""
    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge, CommandType
        body = await request.json()
        command_type_str = body.get("command_type", "")
        parameters = body.get("parameters", {})
        agent_id = body.get("agent_id", "default")
        bridge = AgentEngineBridge.get_instance()
        if not bridge._initialized:
            bridge.initialize()
        command_type = CommandType(command_type_str)
        command = bridge.send_command(command_type, parameters, agent_id)
        return JSONResponse({"status": "success", "data": command.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/agent-engine-bridge/query")
async def agent_engine_bridge_query(request: Request):
    """Query the engine through the bridge."""
    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge, QueryType
        body = await request.json()
        query_type_str = body.get("query_type", "")
        parameters = body.get("parameters", {})
        bridge = AgentEngineBridge.get_instance()
        if not bridge._initialized:
            bridge.initialize()
        query_type = QueryType(query_type_str)
        query = bridge.query(query_type, parameters)
        return JSONResponse({"status": "success", "data": query.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/agent-engine-bridge/action")
async def agent_engine_bridge_action(request: Request):
    """Execute an action through the bridge."""
    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge
        body = await request.json()
        action_type = body.get("action_type", "")
        parameters = body.get("parameters", {})
        bridge = AgentEngineBridge.get_instance()
        if not bridge._initialized:
            bridge.initialize()
        result = bridge.execute_action(action_type, parameters)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/agent-engine-bridge/events")
async def agent_engine_bridge_events(count: int = 50):
    """Get recent events from the bridge."""
    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge
        bridge = AgentEngineBridge.get_instance()
        if not bridge._initialized:
            bridge.initialize()
        events = bridge.get_recent_events(count)
        return JSONResponse({"status": "success", "data": events})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/agent-engine-bridge/sync")
async def agent_engine_bridge_sync():
    """Synchronize agent and engine state."""
    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge
        bridge = AgentEngineBridge.get_instance()
        if not bridge._initialized:
            bridge.initialize()
        result = bridge.sync_state()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/agent-engine-bridge/reset")
async def agent_engine_bridge_reset():
    """Reset the bridge."""
    try:
        from sparkai.engine.engine_agent_bridge import AgentEngineBridge
        bridge = AgentEngineBridge.get_instance()
        bridge.reset()
        return JSONResponse({"status": "success", "data": {"message": "Bridge reset complete"}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Orchestrator Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tool-orchestrator/status")
async def tool_orchestrator_status():
    """Get the current status of the Tool Orchestrator."""
    try:
        from sparkai.agent.agent_tool_orchestrator import AgentToolOrchestrator
        to = AgentToolOrchestrator.get_instance()
        if not to._initialized:
            to.initialize()
        return JSONResponse({"status": "success", "data": to.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/tool-orchestrator/tools")
async def tool_orchestrator_list():
    """List all registered tools."""
    try:
        from sparkai.agent.agent_tool_orchestrator import AgentToolOrchestrator
        to = AgentToolOrchestrator.get_instance()
        if not to._initialized:
            to.initialize()
        tools = list(to._tools.values())
        return JSONResponse({"status": "success", "data": [t.to_dict() for t in tools]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/tool-orchestrator/execute")
async def tool_orchestrator_execute(request: Request):
    """Execute a registered tool."""
    try:
        from sparkai.agent.agent_tool_orchestrator import AgentToolOrchestrator
        body = await request.json()
        tool_name = body.get("tool_name", "")
        parameters = body.get("parameters", {})
        to = AgentToolOrchestrator.get_instance()
        if not to._initialized:
            to.initialize()
        result = to.execute(tool_name, parameters)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/tool-orchestrator/compose")
async def tool_orchestrator_compose(request: Request):
    """Compose and execute a pipeline of tool steps."""
    try:
        from sparkai.agent.agent_tool_orchestrator import AgentToolOrchestrator, ToolStep, CompositionStrategy
        body = await request.json()
        steps_data = body.get("steps", [])
        strategy_str = body.get("strategy", "sequential")
        try:
            strategy = CompositionStrategy(strategy_str)
        except ValueError:
            strategy = CompositionStrategy.SEQUENTIAL
        steps = []
        for s in steps_data:
            steps.append(ToolStep(
                tool_name=s.get("tool_name", ""),
                parameters=s.get("parameters", {}),
                step_id=s.get("step_id", ""),
                condition=s.get("condition"),
                on_failure=s.get("on_failure", "abort"),
            ))
        to = AgentToolOrchestrator.get_instance()
        if not to._initialized:
            to.initialize()
        result = to.compose(steps, strategy)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/tool-orchestrator/history")
async def tool_orchestrator_history(limit: int = Query(default=50, le=200)):
    """Get recent tool execution history."""
    try:
        from sparkai.agent.agent_tool_orchestrator import AgentToolOrchestrator
        to = AgentToolOrchestrator.get_instance()
        if not to._initialized:
            to.initialize()
        history = list(to._execution_history)[-limit:]
        return JSONResponse({"status": "success", "data": [h.to_dict() for h in history]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# World Synthesizer Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/world-synthesizer/status")
async def world_synthesizer_status():
    """Get the current status of the World Synthesizer."""
    try:
        from sparkai.agent.agent_world_synthesizer import AgentWorldSynthesizer
        ws = AgentWorldSynthesizer.get_instance()
        if not ws._initialized:
            ws.initialize()
        return JSONResponse({"status": "success", "data": ws.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/world-synthesizer/generate")
async def world_synthesizer_generate(request: Request):
    """Generate a complete world from a configuration."""
    try:
        from sparkai.agent.agent_world_synthesizer import AgentWorldSynthesizer, WorldConfig, WorldTheme
        body = await request.json()
        theme_str = body.get("theme", "fantasy")
        size = body.get("size", 1024)
        seed = body.get("seed")
        biome_count = body.get("biome_count", 5)
        try:
            theme = WorldTheme(theme_str)
        except ValueError:
            theme = WorldTheme.FANTASY
        config = WorldConfig(
            theme=theme,
            world_size=size,
            seed=seed,
            biome_count=biome_count,
        )
        ws = AgentWorldSynthesizer.get_instance()
        if not ws._initialized:
            ws.initialize()
        terrain = ws.generate_terrain(config)
        ecosystem = ws.place_ecosystem(terrain, config)
        structures = ws.place_structures(terrain, ecosystem, config)
        narrative = ws.seed_narrative(structures, config)
        return JSONResponse({"status": "success", "data": {
            "terrain": terrain.to_dict(),
            "ecosystem": ecosystem.to_dict(),
            "structures": structures.to_dict(),
            "narrative": narrative.to_dict(),
        }})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/world-synthesizer/terrain")
async def world_synthesizer_terrain(request: Request):
    """Generate terrain only."""
    try:
        from sparkai.agent.agent_world_synthesizer import AgentWorldSynthesizer, WorldConfig, WorldTheme
        body = await request.json()
        theme_str = body.get("theme", "fantasy")
        size = body.get("size", 1024)
        seed = body.get("seed")
        try:
            theme = WorldTheme(theme_str)
        except ValueError:
            theme = WorldTheme.FANTASY
        config = WorldConfig(theme=theme, world_size=size, seed=seed)
        ws = AgentWorldSynthesizer.get_instance()
        if not ws._initialized:
            ws.initialize()
        terrain = ws.generate_terrain(config)
        return JSONResponse({"status": "success", "data": terrain.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Semantic Planner Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/semantic-planner/status")
async def semantic_planner_status():
    """Get the current status of the Semantic Planner."""
    try:
        from sparkai.agent.agent_semantic_planner import AgentSemanticPlanner
        sp = AgentSemanticPlanner.get_instance()
        if not sp._initialized:
            sp.initialize()
        return JSONResponse({"status": "success", "data": sp.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/semantic-planner/parse-intent")
async def semantic_planner_parse_intent(request: Request):
    """Parse a natural language intent."""
    try:
        from sparkai.agent.agent_semantic_planner import AgentSemanticPlanner
        body = await request.json()
        text = body.get("text", "")
        context = body.get("context", {})
        sp = AgentSemanticPlanner.get_instance()
        if not sp._initialized:
            sp.initialize()
        intent = sp.parse_intent(text, context)
        return JSONResponse({"status": "success", "data": intent.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/semantic-planner/generate-plan")
async def semantic_planner_generate_plan(request: Request):
    """Generate a plan from a goal description."""
    try:
        from sparkai.agent.agent_semantic_planner import AgentSemanticPlanner, PlanningStrategy, PlanningConstraint
        body = await request.json()
        goal = body.get("goal", "")
        strategy_str = body.get("strategy", "hybrid")
        context = body.get("context", {})
        template_name = body.get("template_name")
        max_steps = body.get("max_steps", 20)
        constraints_data = body.get("constraints", [])
        try:
            strategy = PlanningStrategy(strategy_str)
        except ValueError:
            strategy = PlanningStrategy.HYBRID
        constraints = []
        for c in constraints_data:
            constraints.append(PlanningConstraint(
                constraint_type=c.get("constraint_type", "must_include"),
                target=c.get("target", ""),
                value=c.get("value"),
                priority=c.get("priority", 0),
            ))
        sp = AgentSemanticPlanner.get_instance()
        if not sp._initialized:
            sp.initialize()
        plan = sp.generate_plan(goal, strategy, context, template_name, max_steps, constraints)
        return JSONResponse({"status": "success", "data": plan.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/semantic-planner/validate")
async def semantic_planner_validate(request: Request):
    """Validate a plan for feasibility."""
    try:
        from sparkai.agent.agent_semantic_planner import AgentSemanticPlanner
        body = await request.json()
        plan_id = body.get("plan_id", "")
        sp = AgentSemanticPlanner.get_instance()
        if not sp._initialized:
            sp.initialize()
        result = sp.validate_plan(plan_id)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/semantic-planner/execute")
async def semantic_planner_execute(request: Request):
    """Execute a plan step by step."""
    try:
        from sparkai.agent.agent_semantic_planner import AgentSemanticPlanner
        body = await request.json()
        plan_id = body.get("plan_id", "")
        context = body.get("context", {})
        sp = AgentSemanticPlanner.get_instance()
        if not sp._initialized:
            sp.initialize()
        result = sp.execute_plan(plan_id, context)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/semantic-planner/plans")
async def semantic_planner_list():
    """List all generated plans."""
    try:
        from sparkai.agent.agent_semantic_planner import AgentSemanticPlanner
        sp = AgentSemanticPlanner.get_instance()
        if not sp._initialized:
            sp.initialize()
        plans = [p.to_dict() for p in sp._plans.values()]
        return JSONResponse({"status": "success", "data": plans})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Visual Scripting Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/visual-scripting/status")
async def visual_scripting_status():
    """Get the current status of the Visual Scripting Engine."""
    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        return JSONResponse({"status": "success", "data": vs.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/visual-scripting/graphs")
async def visual_scripting_list():
    """List all script graphs."""
    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        graphs = [g.to_dict() for g in vs._graphs.values()]
        return JSONResponse({"status": "success", "data": graphs})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-scripting/create-graph")
async def visual_scripting_create_graph(request: Request):
    """Create a new visual script graph."""
    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting
        body = await request.json()
        name = body.get("name", f"Graph-{int(time.time())}")
        description = body.get("description", "")
        tags = body.get("tags", [])
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        graph = vs.create_graph(name, description, tags)
        return JSONResponse({"status": "success", "data": graph.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-scripting/add-node")
async def visual_scripting_add_node(request: Request):
    """Add a node to a graph."""
    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting
        body = await request.json()
        graph_id = body.get("graph_id", "")
        node_type = body.get("node_type", "")
        position = tuple(body.get("position", [0.0, 0.0]))
        properties = body.get("properties", {})
        name = body.get("name", "")
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        node = vs.add_node(graph_id, node_type, position, properties, name)
        if node:
            return JSONResponse({"status": "success", "data": node.to_dict()})
        return JSONResponse({"status": "error", "message": "Graph not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-scripting/connect")
async def visual_scripting_connect(request: Request):
    """Connect two nodes in a graph."""
    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting, NodePort
        body = await request.json()
        graph_id = body.get("graph_id", "")
        source_node_id = body.get("source_node_id", "")
        target_node_id = body.get("target_node_id", "")
        source_port = body.get("source_port", "output")
        target_port = body.get("target_port", "input")
        port_type_str = body.get("port_type", "execution")
        label = body.get("label", "")
        try:
            port_type = NodePort(port_type_str)
        except ValueError:
            port_type = NodePort.EXECUTION
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        connection = vs.connect_nodes(graph_id, source_node_id, target_node_id,
                                      source_port, target_port, port_type, label)
        if connection:
            return JSONResponse({"status": "success", "data": connection.to_dict()})
        return JSONResponse({"status": "error", "message": "Connection failed"}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-scripting/execute")
async def visual_scripting_execute(request: Request):
    """Execute a visual script graph."""
    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting
        body = await request.json()
        graph_id = body.get("graph_id", "")
        context = body.get("context", {})
        entry_node_id = body.get("entry_node_id")
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        result = vs.execute_graph(graph_id, context, entry_node_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/visual-scripting/templates")
async def visual_scripting_templates():
    """List all node templates."""
    try:
        from sparkai.engine.engine_visual_scripting import EngineVisualScripting
        vs = EngineVisualScripting.get_instance()
        if not vs._initialized:
            vs.initialize()
        templates = [t.to_dict() for t in vs._templates.values()]
        return JSONResponse({"status": "success", "data": templates})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Cross Platform Builder Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/cross-platform/status")
async def cross_platform_status():
    """Get the current status of the Cross Platform Builder."""
    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        return JSONResponse({"status": "success", "data": cb.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/cross-platform/profiles")
async def cross_platform_profiles():
    """List all platform profiles."""
    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        profiles = [p.to_dict() for p in cb.list_profiles()]
        return JSONResponse({"status": "success", "data": profiles})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/cross-platform/create-profile")
async def cross_platform_create_profile(request: Request):
    """Create a platform build profile."""
    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder
        body = await request.json()
        platform = body.get("platform", "web")
        overrides = body.get("overrides", {})
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        profile = cb.create_platform_profile(platform, overrides)
        return JSONResponse({"status": "success", "data": profile.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/cross-platform/build")
async def cross_platform_build(request: Request):
    """Start a build for a project."""
    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder
        body = await request.json()
        project_id = body.get("project_id", "")
        platform = body.get("platform", "web")
        profile_id = body.get("profile_id")
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        profile = cb.get_profile(profile_id) if profile_id else None
        result = cb.start_build(project_id, platform, profile)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/cross-platform/builds")
async def cross_platform_builds(project_id: Optional[str] = None):
    """List all builds."""
    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        builds = [b.to_dict() for b in cb.list_builds(project_id)]
        return JSONResponse({"status": "success", "data": builds})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/cross-platform/package")
async def cross_platform_package(request: Request):
    """Package assets for a platform."""
    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder, TargetPlatform
        body = await request.json()
        asset_paths = body.get("asset_paths", [])
        platform_str = body.get("platform", "web")
        compression_str = body.get("compression", "balanced")
        try:
            platform = TargetPlatform(platform_str)
        except ValueError:
            platform = TargetPlatform.WEB
        try:
            from sparkai.engine.engine_cross_platform_builder import CompressionLevel
            compression = CompressionLevel(compression_str)
        except ValueError:
            compression = CompressionLevel.BALANCED
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        bundle = cb.package_assets(asset_paths, platform, compression)
        return JSONResponse({"status": "success", "data": bundle.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/cross-platform/defaults/{platform}")
async def cross_platform_defaults(platform: str):
    """Get default configuration for a platform."""
    try:
        from sparkai.engine.engine_cross_platform_builder import EngineCrossPlatformBuilder, TargetPlatform
        try:
            tp = TargetPlatform(platform)
        except ValueError:
            return JSONResponse({"status": "error", "message": f"Unknown platform: {platform}"}, status_code=400)
        cb = EngineCrossPlatformBuilder.get_instance()
        if not cb._initialized:
            cb.initialize()
        defaults = cb.get_platform_defaults(tp)
        serializable = {}
        for k, v in defaults.items():
            if hasattr(v, 'value'):
                serializable[k] = v.value
            else:
                serializable[k] = v
        return JSONResponse({"status": "success", "data": serializable})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Procedural Animation Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/procedural-animation/status")
async def procedural_animation_status():
    """Get the current status of the Procedural Animation Engine."""
    try:
        from sparkai.engine.engine_procedural_animation import EngineProceduralAnimation
        pa = EngineProceduralAnimation.get_instance()
        if not pa._initialized:
            pa.initialize()
        return JSONResponse({"status": "success", "data": pa.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/procedural-animation/skeletons")
async def procedural_animation_skeletons():
    """List all skeletons."""
    try:
        from sparkai.engine.engine_procedural_animation import EngineProceduralAnimation
        pa = EngineProceduralAnimation.get_instance()
        if not pa._initialized:
            pa.initialize()
        skeletons = {sid: {bid: b.to_dict() for bid, b in sk.items()} for sid, sk in pa._skeletons.items()}
        return JSONResponse({"status": "success", "data": skeletons})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/procedural-animation/create-chain")
async def procedural_animation_create_chain(request: Request):
    """Create an IK chain."""
    try:
        from sparkai.engine.engine_procedural_animation import EngineProceduralAnimation, IKAlgorithm
        body = await request.json()
        chain_name = body.get("chain_name", f"Chain-{int(time.time())}")
        bone_ids = body.get("bone_ids", [])
        algorithm_str = body.get("algorithm", "fabrik")
        try:
            algorithm = IKAlgorithm(algorithm_str)
        except ValueError:
            algorithm = IKAlgorithm.FABRIK
        pa = EngineProceduralAnimation.get_instance()
        if not pa._initialized:
            pa.initialize()
        chain = pa.create_ik_chain(chain_name, bone_ids, algorithm)
        return JSONResponse({"status": "success", "data": chain.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/procedural-animation/solve-ik")
async def procedural_animation_solve_ik(request: Request):
    """Solve IK for a chain."""
    try:
        from sparkai.engine.engine_procedural_animation import EngineProceduralAnimation
        body = await request.json()
        chain_id = body.get("chain_id", "")
        skeleton_id = body.get("skeleton_id", "")
        target = body.get("target")
        pa = EngineProceduralAnimation.get_instance()
        if not pa._initialized:
            pa.initialize()
        if target:
            pa.set_ik_target(chain_id, tuple(target))
        result = pa.solve_ik(chain_id, skeleton_id)
        return JSONResponse({"status": "success", "data": {"success": result}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/procedural-animation/locomotion")
async def procedural_animation_locomotion(request: Request):
    """Start procedural locomotion."""
    try:
        from sparkai.engine.engine_procedural_animation import EngineProceduralAnimation, LocomotionType
        body = await request.json()
        entity_id = body.get("entity_id", "")
        locomotion_type_str = body.get("locomotion_type", "walk")
        speed = body.get("speed", 1.0)
        direction = tuple(body.get("direction", [0.0, 0.0, 0.0]))
        try:
            locomotion_type = LocomotionType(locomotion_type_str)
        except ValueError:
            locomotion_type = LocomotionType.WALK
        pa = EngineProceduralAnimation.get_instance()
        if not pa._initialized:
            pa.initialize()
        state = pa.start_locomotion(entity_id, locomotion_type, speed, direction)
        return JSONResponse({"status": "success", "data": state.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/procedural-animation/update")
async def procedural_animation_update(request: Request):
    """Update procedural animation for an entity."""
    try:
        from sparkai.engine.engine_procedural_animation import EngineProceduralAnimation
        body = await request.json()
        entity_id = body.get("entity_id", "")
        delta_time = body.get("delta_time", 0.016)
        pa = EngineProceduralAnimation.get_instance()
        if not pa._initialized:
            pa.initialize()
        pose = pa.update_animation(entity_id, delta_time)
        if pose:
            return JSONResponse({"status": "success", "data": pose.to_dict()})
        return JSONResponse({"status": "error", "message": "Entity not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)