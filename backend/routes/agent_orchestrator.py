"""
SparkLabs API Routes for AI-Native Game Agent Orchestrator.

Provides endpoints for the ultimate AI-native game agent orchestrator
that integrates all agent subsystems for autonomous game creation,
execution, world simulation, quality assurance, and deployment.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import time

router = APIRouter(tags=["Agent Orchestrator"])


# ═══════════════════════════════════════════════════════════════════════════════
# Orchestrator Core Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ai-native-orchestrator/status")
async def orchestrator_status():
    """Get the current status of the AI-Native Orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        return JSONResponse({"status": "success", "data": orch.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/initialize")
async def orchestrator_initialize(request: Request):
    """Initialize the AI-Native Orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orch = get_ai_native_orchestrator()
        orch.initialize()
        return JSONResponse({"status": "success", "data": orch.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/shutdown")
async def orchestrator_shutdown():
    """Shutdown the AI-Native Orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orch = get_ai_native_orchestrator()
        orch.shutdown()
        return JSONResponse({"status": "success", "data": {"shutdown": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-orchestrator/subsystems")
async def orchestrator_subsystems():
    """Get the status of all subsystems."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        status = orch.get_status()
        return JSONResponse({"status": "success", "data": status.get("subsystems_available", {})})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-orchestrator/history")
async def orchestrator_history(limit: int = Query(default=50, le=200)):
    """Get recent operation history."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        history = orch.get_operation_history(limit=limit)
        return JSONResponse({"status": "success", "data": history})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Game Creation Pipeline Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ai-native-orchestrator/create-game")
async def orchestrator_create_game(request: Request):
    """Create a complete game from natural language description."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        description = body.get("description", "")
        context = body.get("context", {})
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.create_game_from_description(description, context)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/parse-idea")
async def orchestrator_parse_idea(request: Request):
    """Parse a game idea from natural language description."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        description = body.get("description", "")
        context = body.get("context", {})
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.parse_game_idea(description, context)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/design-game")
async def orchestrator_design_game(request: Request):
    """Generate a complete game design document from an idea."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        idea_id = body.get("idea_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.design_game(idea_id)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/scaffold-project")
async def orchestrator_scaffold_project(request: Request):
    """Generate project scaffolding from a game design."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        design_id = body.get("design_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.scaffold_project_by_id(design_id)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/generate-code")
async def orchestrator_generate_code(request: Request):
    """Generate game code from a design document."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        design_id = body.get("design_id", "")
        language = body.get("language", "python")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.generate_code(design_id, language)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/generate-assets")
async def orchestrator_generate_assets(request: Request):
    """Generate game assets from a design document."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        design_id = body.get("design_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.generate_assets(design_id)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/build-scenes")
async def orchestrator_build_scenes(request: Request):
    """Build game scenes from a design document."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        design_id = body.get("design_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.build_scenes(design_id)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Game Execution Pipeline Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ai-native-orchestrator/launch-game")
async def orchestrator_launch_game(request: Request):
    """Launch a game for execution."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        project_id = body.get("project_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.launch_game(project_id)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/stop-game")
async def orchestrator_stop_game(request: Request):
    """Stop a running game."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        game_id = body.get("game_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.stop_game(game_id)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-orchestrator/running-games")
async def orchestrator_running_games():
    """List all currently running games."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.list_running_games()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-orchestrator/performance-metrics")
async def orchestrator_performance_metrics(game_id: Optional[str] = Query(None)):
    """Get performance metrics for a running game."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.get_performance_metrics(game_id)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# World Generation Pipeline Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ai-native-orchestrator/generate-world")
async def orchestrator_generate_world(request: Request):
    """Generate and simulate a complete game world."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        world_name = body.get("world_name", "New World")
        theme = body.get("theme", "fantasy")
        width = body.get("width", 2048)
        height = body.get("height", 2048)
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.generate_and_simulate_world(
            description=world_name, theme=theme, width=width, height=height
        )
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/simulate-world")
async def orchestrator_simulate_world(request: Request):
    """Run world simulation ticks."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        world_id = body.get("world_id", "")
        ticks = body.get("ticks", 100)
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.simulate_world_by_id(world_id, ticks)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Quality Pipeline Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ai-native-orchestrator/run-quality")
async def orchestrator_run_quality(request: Request):
    """Run the complete quality assurance pipeline."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        project_id = body.get("project_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.run_full_quality_pipeline(project_id)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/run-tests")
async def orchestrator_run_tests(request: Request):
    """Run automated tests on a project."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        project_id = body.get("project_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.run_automated_tests(project_id)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/analyze-quality")
async def orchestrator_analyze_quality(request: Request):
    """Analyze code and design quality."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        project_id = body.get("project_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.analyze_quality_by_id(project_id)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Deployment Pipeline Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ai-native-orchestrator/deploy")
async def orchestrator_deploy(request: Request):
    """Deploy a game to a target platform."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        project_id = body.get("project_id", "")
        platform = body.get("platform", "web")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.deploy_game(project_id, platform)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-native-orchestrator/optimize-performance")
async def orchestrator_optimize_performance(request: Request):
    """Run automatic performance optimization."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        body = await request.json()
        project_id = body.get("project_id", "")
        orch = get_ai_native_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.optimize_performance(project_id)
        return JSONResponse({"status": "success", "data": result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-native-orchestrator/platforms")
async def orchestrator_platforms():
    """List available deployment platforms."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import Platform
        platforms = [{"name": p.value, "label": p.name} for p in Platform]
        return JSONResponse({"status": "success", "data": platforms})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)