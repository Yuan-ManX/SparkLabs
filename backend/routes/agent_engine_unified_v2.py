"""
SparkLabs Backend - Unified Agent & Engine Core API Routes

Comprehensive REST API endpoints for the UnifiedAgentCore and UnifiedGameEngine
systems. Provides complete integration between the agent layer, engine layer,
and frontend web interface. All endpoints are designed for the AI-native
game development workflow.

Routes:
  /api/unified/agent/*     - Unified Agent Core operations
  /api/unified/engine/*    - Unified Game Engine operations
  /api/unified/bridge/*    - Agent-Engine bridge operations
  /api/unified/system/*    - System status and orchestration
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import time

router = APIRouter(tags=["Unified Agent & Engine Core"])


# =============================================================================
# Unified Agent Core Routes
# =============================================================================


@router.get("/unified/agent/status")
async def unified_agent_status():
    """Get comprehensive status of the Unified Agent Core."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        return JSONResponse({"status": "success", "data": core.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/initialize")
async def unified_agent_initialize():
    """Initialize the Unified Agent Core."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        core.initialize()
        return JSONResponse({"status": "success", "data": {"initialized": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/reason")
async def unified_agent_reason(request: Request):
    """Apply reasoning to a task."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core, ReasoningDepth
        body = await request.json()
        task = body.get("task", "")
        depth_str = body.get("depth", "standard")
        context = body.get("context", None)
        depth_map = {
            "instant": ReasoningDepth.INSTANT, "surface": ReasoningDepth.SURFACE,
            "standard": ReasoningDepth.STANDARD, "deep": ReasoningDepth.DEEP,
            "exhaustive": ReasoningDepth.EXHAUSTIVE,
        }
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.reason(task, context, depth_map.get(depth_str, ReasoningDepth.STANDARD))
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/plan")
async def unified_agent_plan(request: Request):
    """Generate a plan for given goals."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        goals = body.get("goals", [])
        context = body.get("context", None)
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.plan(goals, context)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/execute")
async def unified_agent_execute(request: Request):
    """Execute an action through the cognitive layer."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        action_name = body.get("action_name", "")
        parameters = body.get("parameters", {})
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.execute_action(action_name, parameters)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/reflect")
async def unified_agent_reflect():
    """Self-reflect on recent actions."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.reflect()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# -------------------------------------------------------------------------
# Memory Operations
# -------------------------------------------------------------------------


@router.post("/unified/agent/memory/store")
async def unified_agent_memory_store(request: Request):
    """Store a memory entry."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core, MemoryType
        body = await request.json()
        memory_type_str = body.get("memory_type", "episodic")
        content = body.get("content", {})
        importance = body.get("importance", 0.5)
        tags = body.get("tags", [])
        try:
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            memory_type = MemoryType.EPISODIC
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        entry_id = core.remember(memory_type, content, importance, tags)
        return JSONResponse({"status": "success", "data": {"entry_id": entry_id}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/memory/recall")
async def unified_agent_memory_recall(request: Request):
    """Retrieve memories matching a query."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core, MemoryType
        body = await request.json()
        memory_type_str = body.get("memory_type", "episodic")
        query = body.get("query", {})
        try:
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            memory_type = MemoryType.EPISODIC
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.recall(memory_type, query)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/agent/memory/recall-by-tags")
async def unified_agent_memory_recall_by_tags(tags: str = Query(default="")):
    """Retrieve memories by tags (comma-separated)."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.recall_by_tags(tag_list)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# -------------------------------------------------------------------------
# Game Creation Operations
# -------------------------------------------------------------------------


@router.post("/unified/agent/create-game")
async def unified_agent_create_game(request: Request):
    """Create a complete game from a natural language description."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        prompt = body.get("prompt", "")
        genre = body.get("genre", None)
        quality = body.get("quality", "playable")
        style = body.get("style", "flat_2d")
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        project = core.create_game(prompt, genre, quality, style)
        return JSONResponse({"status": "success", "data": project.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/agent/projects")
async def unified_agent_list_projects():
    """List all game projects."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        projects = core.list_projects()
        return JSONResponse({"status": "success", "data": projects})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/agent/project/{project_id}")
async def unified_agent_get_project(project_id: str):
    """Get a specific game project."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        project = core.get_project(project_id)
        if project is None:
            return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": project})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/project/{project_id}/playtest")
async def unified_agent_playtest(project_id: str):
    """Run playtesting on a game project."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.playtest_game(project_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/project/{project_id}/iterate")
async def unified_agent_iterate(project_id: str, request: Request):
    """Iterate on a game project based on feedback."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        feedback = body.get("feedback", "")
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.iterate_game(project_id, feedback)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# -------------------------------------------------------------------------
# World Operations
# -------------------------------------------------------------------------


@router.post("/unified/agent/generate-world")
async def unified_agent_generate_world(request: Request):
    """Generate a complete game world."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        description = body.get("description", "A procedurally generated world")
        width = body.get("width", 1024)
        height = body.get("height", 1024)
        seed = body.get("seed", None)
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        world = core.generate_world(description, width, height, seed)
        return JSONResponse({"status": "success", "data": world.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/world/{world_id}/simulate")
async def unified_agent_simulate_world(world_id: str, request: Request):
    """Run world simulation."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        ticks = body.get("ticks", 100)
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.simulate_world(world_id, ticks)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/world/{world_id}/evolve")
async def unified_agent_evolve_world(world_id: str, request: Request):
    """Evolve a world through generations."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        generations = body.get("generations", 10)
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.evolve_world(world_id, generations)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# -------------------------------------------------------------------------
# Team Operations
# -------------------------------------------------------------------------


@router.post("/unified/agent/team/form")
async def unified_agent_form_team(request: Request):
    """Form a multi-agent team."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        team_name = body.get("team_name", "Team")
        roles = body.get("roles", ["coordinator", "programmer"])
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.form_team(team_name, roles)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/team/{team_id}/task")
async def unified_agent_assign_task(team_id: str, request: Request):
    """Assign a task to a team."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        description = body.get("description", "")
        roles = body.get("roles", ["coordinator"])
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        task = core.assign_task(team_id, description, roles)
        return JSONResponse({"status": "success", "data": task.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/task/{task_id}/execute")
async def unified_agent_execute_task(task_id: str):
    """Execute a team task."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.execute_team_task(task_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# -------------------------------------------------------------------------
# Tool Operations
# -------------------------------------------------------------------------


@router.get("/unified/agent/tools")
async def unified_agent_list_tools(category: str = Query(default="")):
    """List available tools, optionally filtered by category."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        tools = core.list_tools(category if category else None)
        return JSONResponse({"status": "success", "data": tools})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/tool/execute")
async def unified_agent_execute_tool(request: Request):
    """Execute a tool."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        tool_name = body.get("tool_name", "")
        parameters = body.get("parameters", {})
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.execute_tool(tool_name, parameters)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/tool/chain")
async def unified_agent_create_tool_chain(request: Request):
    """Create a tool execution chain."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        chain_name = body.get("chain_name", "")
        tool_names = body.get("tool_names", [])
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.create_tool_chain(chain_name, tool_names)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/tool/chain/execute")
async def unified_agent_execute_tool_chain(request: Request):
    """Execute a tool chain."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        chain_name = body.get("chain_name", "")
        parameters = body.get("parameters", {})
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.execute_tool_chain(chain_name, parameters)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# -------------------------------------------------------------------------
# Learning Operations
# -------------------------------------------------------------------------


@router.post("/unified/agent/learn")
async def unified_agent_learn(request: Request):
    """Record a learning experience."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        body = await request.json()
        experience = body.get("experience", {})
        outcome = body.get("outcome", "success")
        lessons = body.get("lessons", [])
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.learn(experience, outcome, lessons)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/agent/evolve")
async def unified_agent_evolve():
    """Run a skill evolution cycle."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        result = core.evolve()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/agent/skills")
async def unified_agent_skills():
    """Get current skill levels."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        core = get_unified_agent_core()
        if not core._initialized:
            core.initialize()
        skills = core.get_skill_levels()
        return JSONResponse({"status": "success", "data": skills})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Unified Game Engine Routes
# =============================================================================


@router.get("/unified/engine/status")
async def unified_engine_status():
    """Get comprehensive status of the Unified Game Engine."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        return JSONResponse({"status": "success", "data": engine.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/initialize")
async def unified_engine_initialize():
    """Initialize the Unified Game Engine."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        engine = get_unified_game_engine()
        engine.initialize()
        return JSONResponse({"status": "success", "data": {"initialized": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/scene")
async def unified_engine_create_scene(request: Request):
    """Create a new game scene."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        body = await request.json()
        name = body.get("name", "Untitled Scene")
        width = body.get("width", 1920)
        height = body.get("height", 1080)
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        scene = engine.create_scene(name, width, height)
        return JSONResponse({"status": "success", "data": scene.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/scene/{scene_id}/load")
async def unified_engine_load_scene(scene_id: str):
    """Load and activate a scene."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        scene = engine.load_scene(scene_id)
        return JSONResponse({"status": "success", "data": scene.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/scene/{scene_id}/entity")
async def unified_engine_spawn_entity(scene_id: str, request: Request):
    """Spawn an entity in a scene."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine, EntityType
        body = await request.json()
        name = body.get("name", "Entity")
        entity_type_str = body.get("entity_type", "custom")
        x = body.get("x", 0.0)
        y = body.get("y", 0.0)
        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            entity_type = EntityType.CUSTOM
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        entity = engine.spawn_entity(scene_id, name, entity_type, x, y)
        return JSONResponse({"status": "success", "data": entity.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/unified/engine/scene/{scene_id}/entity/{entity_id}")
async def unified_engine_remove_entity(scene_id: str, entity_id: str):
    """Remove an entity from a scene."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        removed = engine.remove_entity(scene_id, entity_id)
        return JSONResponse({"status": "success", "data": {"removed": removed}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/physics/body")
async def unified_engine_create_physics_body(request: Request):
    """Create a physics body."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine, PhysicsBody, PhysicsShape
        body = await request.json()
        shape_str = body.get("shape", "box")
        try:
            shape = PhysicsShape(shape_str)
        except ValueError:
            shape = PhysicsShape.BOX
        physics_body = PhysicsBody(
            body_id=f"body_{uuid.uuid4().hex[:8]}",
            entity_id=body.get("entity_id", ""),
            shape=shape,
            mass=body.get("mass", 1.0),
            is_static=body.get("is_static", False),
            friction=body.get("friction", 0.5),
            restitution=body.get("restitution", 0.3),
        )
        import uuid
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        body_id = engine.create_physics_body(physics_body)
        return JSONResponse({"status": "success", "data": {"body_id": body_id}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/physics/force")
async def unified_engine_apply_force(request: Request):
    """Apply a force to a physics body."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        body = await request.json()
        body_id = body.get("body_id", "")
        force_x = body.get("force_x", 0.0)
        force_y = body.get("force_y", 0.0)
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        engine.apply_force(body_id, force_x, force_y)
        return JSONResponse({"status": "success", "data": {"applied": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/tick")
async def unified_engine_tick():
    """Execute a single game loop tick."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        stats = engine.tick()
        return JSONResponse({"status": "success", "data": stats.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/simulate")
async def unified_engine_simulate(request: Request):
    """Run a headless simulation for a number of frames."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        body = await request.json()
        num_frames = body.get("num_frames", 100)
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        stats_list = engine.run_simulation(num_frames)
        return JSONResponse({
            "status": "success",
            "data": {
                "frames_simulated": len(stats_list),
                "average_fps": sum(s.fps for s in stats_list) / max(len(stats_list), 1),
                "last_frame": stats_list[-1].to_dict() if stats_list else None,
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/generate-world")
async def unified_engine_generate_world(request: Request):
    """Generate a procedurally generated world."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        body = await request.json()
        width = body.get("width", 100)
        height = body.get("height", 100)
        seed = body.get("seed", None)
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        world = engine.generate_world(width, height, seed)
        return JSONResponse({"status": "success", "data": world})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/weather")
async def unified_engine_set_weather(request: Request):
    """Set weather conditions."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        body = await request.json()
        weather_type = body.get("weather_type", "clear")
        temperature = body.get("temperature", 22.0)
        humidity = body.get("humidity", 0.5)
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        engine.set_weather(weather_type, temperature, humidity)
        return JSONResponse({"status": "success", "data": {"weather_set": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/engine/input")
async def unified_engine_simulate_input(request: Request):
    """Simulate an input action."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine, InputAction
        body = await request.json()
        action_str = body.get("action", "jump")
        pressed = body.get("pressed", True)
        try:
            action = InputAction(action_str)
        except ValueError:
            action = InputAction.JUMP
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        engine.simulate_input(action, pressed)
        return JSONResponse({"status": "success", "data": {"action": action_str, "pressed": pressed}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Agent-Engine Bridge Routes
# =============================================================================


@router.post("/unified/bridge/command")
async def unified_bridge_command(request: Request):
    """Send a command from agent to engine."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        body = await request.json()
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        result = engine.process_agent_command(body)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/bridge/events")
async def unified_bridge_events(limit: int = Query(default=50, le=200)):
    """Get engine events for the agent."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        events = engine.get_agent_events(limit)
        return JSONResponse({"status": "success", "data": events})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/bridge/emit")
async def unified_bridge_emit(request: Request):
    """Emit an engine event to the agent."""
    try:
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        body = await request.json()
        event_type = body.get("event_type", "")
        event_data = body.get("event_data", {})
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        engine.emit_engine_event(event_type, event_data)
        return JSONResponse({"status": "success", "data": {"emitted": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# System Orchestration Routes
# =============================================================================


@router.get("/unified/system/status")
async def unified_system_status():
    """Get combined status of both agent and engine systems."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        agent_core = get_unified_agent_core()
        if not agent_core._initialized:
            agent_core.initialize()
        engine = get_unified_game_engine()
        if not engine._initialized:
            engine.initialize()
        return JSONResponse({
            "status": "success",
            "data": {
                "agent": agent_core.get_status(),
                "engine": engine.get_status(),
                "integrated": True,
                "timestamp": time.time(),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/system/initialize-all")
async def unified_system_initialize_all():
    """Initialize both agent and engine systems."""
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine
        agent_core = get_unified_agent_core()
        agent_core.initialize()
        engine = get_unified_game_engine()
        engine.initialize()
        return JSONResponse({
            "status": "success",
            "data": {
                "agent_initialized": agent_core._initialized,
                "engine_initialized": engine._initialized,
                "timestamp": time.time(),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/system/end-to-end")
async def unified_system_end_to_end(request: Request):
    """
    Run a complete end-to-end workflow: create game, generate world,
    build scene, simulate gameplay, and report results.
    """
    try:
        from sparkai.agent.agent_unified_agent_core import get_unified_agent_core
        from sparkai.engine.engine_unified_game_engine import get_unified_game_engine

        body = await request.json()
        prompt = body.get("prompt", "A 2D platformer game")

        # Initialize both systems
        agent_core = get_unified_agent_core()
        agent_core.initialize()
        engine = get_unified_game_engine()
        engine.initialize()

        result = {
            "workflow": "end-to-end",
            "timestamp": time.time(),
            "steps": [],
        }

        # Step 1: Create game
        project = agent_core.create_game(prompt, quality="playable", style="flat_2d")
        result["steps"].append({
            "step": "create_game",
            "status": "completed",
            "project_id": project.project_id,
            "title": project.title,
        })

        # Step 2: Generate world
        world = agent_core.generate_world(f"World for {prompt[:50]}", 256, 256)
        result["steps"].append({
            "step": "generate_world",
            "status": "completed",
            "world_id": world.world_id,
            "tiles": world.width * world.height,
        })

        # Step 3: Create engine scene
        scene = engine.create_scene(project.title, 1920, 1080)
        engine.load_scene(scene.scene_id)
        result["steps"].append({
            "step": "create_scene",
            "status": "completed",
            "scene_id": scene.scene_id,
        })

        # Step 4: Spawn entities
        entities_spawned = []
        for i in range(5):
            entity = engine.spawn_entity(
                scene.scene_id, f"Entity_{i}",
                "custom" if i > 0 else "player",
                i * 100.0, i * 50.0
            )
            entities_spawned.append(entity.entity_id)
        result["steps"].append({
            "step": "spawn_entities",
            "status": "completed",
            "entities": entities_spawned,
        })

        # Step 5: Run simulation
        simulation = engine.run_simulation(30)
        result["steps"].append({
            "step": "run_simulation",
            "status": "completed",
            "frames": len(simulation),
            "average_fps": sum(s.fps for s in simulation) / max(len(simulation), 1),
        })

        # Step 6: Playtest
        playtest = agent_core.playtest_game(project.project_id)
        result["steps"].append({
            "step": "playtest",
            "status": "completed",
            "fun_score": playtest.get("gameplay_metrics", {}).get("fun_score", 0),
        })

        # Step 7: Learn
        learning = agent_core.learn(
            {"workflow": "end-to-end", "prompt": prompt},
            "success",
            ["End-to-end workflow completed successfully", "All systems integrated properly"]
        )
        result["steps"].append({
            "step": "learn",
            "status": "completed",
            "record_id": learning.get("record_id"),
        })

        result["summary"] = {
            "total_steps": len(result["steps"]),
            "all_successful": all(s["status"] == "completed" for s in result["steps"]),
            "project_id": project.project_id,
            "world_id": world.world_id,
            "scene_id": scene.scene_id,
        }

        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# AI-Native Game Orchestrator Routes
# =============================================================================


@router.post("/unified/orchestrator/initialize")
async def unified_orchestrator_initialize():
    """Initialize the AI-Native Game Orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        orchestrator.initialize()
        return JSONResponse({"status": "success", "data": {"initialized": orchestrator._initialized}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/orchestrator/status")
async def unified_orchestrator_status():
    """Get comprehensive status of the AI-Native Game Orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        return JSONResponse({"status": "success", "data": orchestrator.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/orchestrator/create-game")
async def unified_orchestrator_create_game(request: Request):
    """Create a complete game from a natural language description using the orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        prompt = body.get("prompt", "")
        genre = body.get("genre", None)
        quality = body.get("quality", "playable")
        style = body.get("style", "flat_2d")
        auto_playtest = body.get("auto_playtest", True)
        auto_optimize = body.get("auto_optimize", True)
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        result = orchestrator.create_game(prompt, genre, quality, style, auto_playtest, auto_optimize)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/orchestrator/analyze-game/{project_id}")
async def unified_orchestrator_analyze_game(project_id: str):
    """Perform comprehensive analysis of a game project."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        analysis = orchestrator.analyze_game(project_id)
        return JSONResponse({"status": "success", "data": analysis.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/orchestrator/run-learning-cycle")
async def unified_orchestrator_run_learning_cycle():
    """Run a complete self-improvement learning cycle."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        result = orchestrator.run_learning_cycle()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/orchestrator/phase/{phase_name}")
async def unified_orchestrator_execute_phase(phase_name: str, request: Request):
    """Execute a specific development phase of the game creation pipeline."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import (
            get_ai_native_orchestrator,
            GameDevelopmentPhase,
        )
        body = await request.json()
        context = body.get("context", {})
        try:
            phase = GameDevelopmentPhase(phase_name)
        except ValueError:
            valid_phases = [p.value for p in GameDevelopmentPhase]
            return JSONResponse({
                "status": "error",
                "message": f"Invalid phase '{phase_name}'. Valid phases: {valid_phases}",
            }, status_code=400)
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        orchestrator._transition_phase(phase)
        result = orchestrator._execute_phase(phase, context)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/orchestrator/sessions")
async def unified_orchestrator_list_sessions():
    """List all development sessions managed by the orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        sessions = {
            session_id: session.to_dict()
            for session_id, session in orchestrator._sessions.items()
        }
        return JSONResponse({"status": "success", "data": sessions})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/unified/orchestrator/session/{session_id}")
async def unified_orchestrator_get_session(session_id: str):
    """Get a specific development session by ID."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        session = orchestrator._sessions.get(session_id)
        if session is None:
            return JSONResponse({
                "status": "error",
                "message": f"Session '{session_id}' not found",
            }, status_code=404)
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/orchestrator/auto-optimize/{project_id}")
async def unified_orchestrator_auto_optimize(project_id: str):
    """Auto-optimize a game project based on playtesting results."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        playtest_result = orchestrator._run_playtest(project_id)
        optimization_result = orchestrator._run_optimization(project_id, playtest_result)
        return JSONResponse({
            "status": "success",
            "data": {
                "project_id": project_id,
                "playtest": playtest_result,
                "optimization": optimization_result,
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Game Intelligence Hub Routes
# =============================================================================


@router.get("/unified/intelligence/status")
async def unified_intelligence_hub_status():
    """Get comprehensive status of the Game Intelligence Hub."""
    try:
        from sparkai.agent.agent_game_intelligence_hub import get_game_intelligence_hub
        hub = get_game_intelligence_hub()
        if not hub._initialized:
            hub.initialize()
        return JSONResponse({"status": "success", "data": hub.get_status().to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/intelligence/initialize")
async def unified_intelligence_hub_initialize():
    """Initialize the Game Intelligence Hub."""
    try:
        from sparkai.agent.agent_game_intelligence_hub import get_game_intelligence_hub
        hub = get_game_intelligence_hub()
        hub.initialize()
        return JSONResponse({"status": "success", "data": {"initialized": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/intelligence/analyze")
async def unified_intelligence_analyze(request: Request):
    """Perform comprehensive game analysis across all dimensions."""
    try:
        from sparkai.agent.agent_game_intelligence_hub import get_game_intelligence_hub
        body = await request.json()
        game_id = body.get("game_id", "default")
        hub = get_game_intelligence_hub()
        if not hub._initialized:
            hub.initialize()
        result = hub.analyze_game(game_id)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/intelligence/decide")
async def unified_intelligence_decide(request: Request):
    """Make an AI-driven game design decision."""
    try:
        from sparkai.agent.agent_game_intelligence_hub import get_game_intelligence_hub
        body = await request.json()
        context = body.get("context", {})
        priority = body.get("priority", "medium")
        from sparkai.agent.agent_game_intelligence_hub import DecisionPriority
        hub = get_game_intelligence_hub()
        if not hub._initialized:
            hub.initialize()
        result = hub.make_decision(context, DecisionPriority(priority))
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/intelligence/suggest-improvements")
async def unified_intelligence_suggest_improvements(request: Request):
    """Generate prioritized improvement suggestions for a game."""
    try:
        from sparkai.agent.agent_game_intelligence_hub import get_game_intelligence_hub
        body = await request.json()
        game_id = body.get("game_id", "default")
        hub = get_game_intelligence_hub()
        if not hub._initialized:
            hub.initialize()
        result = hub.suggest_improvements(game_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Agent-Engine Communication Protocol Routes
# =============================================================================


@router.get("/unified/protocol/status")
async def unified_protocol_status():
    """Get comprehensive status of the communication protocol."""
    try:
        from sparkai.agent.agent_engine_communication_protocol import get_communication_protocol, ProtocolState
        import json
        protocol = get_communication_protocol()
        if protocol._state == ProtocolState.DISCONNECTED:
            protocol.initialize()
        data = protocol.get_status()
        return JSONResponse({"status": "success", "data": json.loads(json.dumps(data, default=lambda o: o.value if hasattr(o, 'value') else str(o)))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/protocol/initialize")
async def unified_protocol_initialize():
    """Initialize the communication protocol."""
    try:
        from sparkai.agent.agent_engine_communication_protocol import get_communication_protocol
        protocol = get_communication_protocol()
        protocol.initialize()
        return JSONResponse({"status": "success", "data": {"initialized": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/protocol/command")
async def unified_protocol_send_command(request: Request):
    """Send a command from agent to engine."""
    try:
        from sparkai.agent.agent_engine_communication_protocol import (
            get_communication_protocol, AgentCommand, CommandType, ProtocolState
        )
        import json
        body = await request.json()
        protocol = get_communication_protocol()
        if protocol._state == ProtocolState.DISCONNECTED:
            protocol.initialize()
        command = AgentCommand(
            command_type=CommandType[body.get("command_type", "SPAWN_ENTITY").upper()],
            target_entity_id=body.get("target_id", ""),
            parameters=body.get("parameters", {}),
            priority=body.get("priority", 0.5),
        )
        result = protocol.execute_command(command)
        return JSONResponse({"status": "success", "data": json.loads(json.dumps(result, default=lambda o: o.value if hasattr(o, 'value') else str(o)))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/protocol/query")
async def unified_protocol_query(request: Request):
    """Query the engine for state information."""
    try:
        from sparkai.agent.agent_engine_communication_protocol import (
            get_communication_protocol, EngineQuery, QueryType, ProtocolState
        )
        import json
        body = await request.json()
        protocol = get_communication_protocol()
        if protocol._state == ProtocolState.DISCONNECTED:
            protocol.initialize()
        query = EngineQuery(
            query_type=QueryType[body.get("query_type", "GET_ENTITY").upper()],
            target=body.get("target_id", ""),
            filters=body.get("parameters", {}),
        )
        result = protocol.query_engine(query)
        return JSONResponse({"status": "success", "data": json.loads(json.dumps(result, default=lambda o: o.value if hasattr(o, 'value') else str(o)))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/protocol/sync")
async def unified_protocol_sync(request: Request):
    """Synchronize state between agent and engine."""
    try:
        from sparkai.agent.agent_engine_communication_protocol import (
            get_communication_protocol, SyncMode, ProtocolState
        )
        import json
        body = await request.json()
        mode = body.get("mode", "FULL").upper()
        protocol = get_communication_protocol()
        if protocol._state == ProtocolState.DISCONNECTED:
            protocol.initialize()
        result = protocol.sync_state(SyncMode[mode])
        return JSONResponse({"status": "success", "data": json.loads(json.dumps(result, default=lambda o: o.value if hasattr(o, 'value') else str(o)))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Runtime Executor Routes
# =============================================================================


@router.get("/unified/executor/status")
async def unified_executor_status():
    """Get comprehensive status of the runtime executor."""
    try:
        from sparkai.engine.engine_runtime_executor import get_runtime_executor, ExecutorState, ExecutorConfig
        import json
        executor = get_runtime_executor()
        if executor._state == ExecutorState.UNINITIALIZED:
            executor.initialize(ExecutorConfig())
        data = executor.get_status()
        return JSONResponse({"status": "success", "data": json.loads(json.dumps(data, default=lambda o: o.value if hasattr(o, 'value') else str(o)))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/executor/initialize")
async def unified_executor_initialize():
    """Initialize the runtime executor."""
    try:
        from sparkai.engine.engine_runtime_executor import get_runtime_executor, ExecutorConfig
        executor = get_runtime_executor()
        config = ExecutorConfig()
        executor.initialize(config)
        return JSONResponse({"status": "success", "data": {"initialized": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/executor/load-game")
async def unified_executor_load_game(request: Request):
    """Load a game into the runtime executor."""
    try:
        from sparkai.engine.engine_runtime_executor import get_runtime_executor, ExecutorState, ExecutorConfig
        body = await request.json()
        executor = get_runtime_executor()
        if executor._state == ExecutorState.UNINITIALIZED:
            executor.initialize(ExecutorConfig())
        game_id = executor.load_game(body.get("game_data", {}))
        return JSONResponse({"status": "success", "data": {"game_id": game_id}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/executor/start/{game_id}")
async def unified_executor_start_game(game_id: str):
    """Start executing a loaded game."""
    try:
        from sparkai.engine.engine_runtime_executor import get_runtime_executor, ExecutorState, ExecutorConfig
        executor = get_runtime_executor()
        if executor._state == ExecutorState.UNINITIALIZED:
            executor.initialize(ExecutorConfig())
        executor.start_game(game_id)
        return JSONResponse({"status": "success", "data": {"game_id": game_id, "running": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/executor/stop/{game_id}")
async def unified_executor_stop_game(game_id: str):
    """Stop executing a game."""
    try:
        from sparkai.engine.engine_runtime_executor import get_runtime_executor
        executor = get_runtime_executor()
        executor.stop_game(game_id)
        return JSONResponse({"status": "success", "data": {"game_id": game_id, "running": False}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/executor/step/{game_id}")
async def unified_executor_step_frame(game_id: str):
    """Execute a single frame for debugging."""
    try:
        from sparkai.engine.engine_runtime_executor import get_runtime_executor, ExecutorState, ExecutorConfig
        import json
        executor = get_runtime_executor()
        if executor._state == ExecutorState.UNINITIALIZED:
            executor.initialize(ExecutorConfig())
        result = executor.step_frame(game_id)
        return JSONResponse({"status": "success", "data": json.loads(json.dumps(result, default=lambda o: o.value if hasattr(o, 'value') else str(o)))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/unified/executor/profile/{game_id}")
async def unified_executor_profile_game(game_id: str, request: Request):
    """Profile game performance."""
    try:
        from sparkai.engine.engine_runtime_executor import get_runtime_executor, ExecutorState, ExecutorConfig
        import json
        body = await request.json()
        duration = body.get("duration", 5.0)
        executor = get_runtime_executor()
        if executor._state == ExecutorState.UNINITIALIZED:
            executor.initialize(ExecutorConfig())
        result = executor.profile_game(game_id, duration)
        return JSONResponse({"status": "success", "data": json.loads(json.dumps(result, default=lambda o: o.value if hasattr(o, 'value') else str(o)))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)