"""
SparkLabs Backend - AI-Native Game Orchestrator Routes

Standalone API endpoints for the AINativeGameOrchestrator. Provides
complete access to the orchestrator's game creation pipeline, analysis,
self-evolution, and session management capabilities.

Routes:
  /orchestrator/initialize          - Initialize the orchestrator
  /orchestrator/status              - Get orchestrator status
  /orchestrator/create-game         - Create a complete game
  /orchestrator/analyze-game/{id}   - Analyze a game project
  /orchestrator/run-learning-cycle  - Run self-improvement
  /orchestrator/phase/{name}        - Execute a development phase
  /orchestrator/sessions            - List all sessions
  /orchestrator/session/{id}        - Get a specific session
  /orchestrator/auto-optimize/{id}  - Auto-optimize a game
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


# =============================================================================
# Orchestrator Initialization & Status
# =============================================================================


@router.post("/orchestrator/initialize")
async def orchestrator_initialize():
    """Initialize the AI-Native Game Orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        orchestrator.initialize()
        return JSONResponse({"status": "success", "data": {"initialized": orchestrator._initialized}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/orchestrator/status")
async def orchestrator_status():
    """Get comprehensive status of the AI-Native Game Orchestrator."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        return JSONResponse({"status": "success", "data": orchestrator.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Game Creation
# =============================================================================


@router.post("/orchestrator/create-game")
async def orchestrator_create_game(request: Request):
    """Create a complete game from a natural language description using the orchestrator.

    Request body:
        - prompt: Natural language description of the desired game
        - genre: Optional game genre (platformer, rpg, shooter, etc.)
        - quality: Quality level (prototype, playable, polished, production)
        - style: Visual asset style (pixel_art, flat_2d, cartoon, etc.)
        - auto_playtest: Automatically run playtesting after creation
        - auto_optimize: Automatically optimize based on playtest results
    """
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


# =============================================================================
# Game Analysis
# =============================================================================


@router.post("/orchestrator/analyze-game/{project_id}")
async def orchestrator_analyze_game(project_id: str):
    """Perform comprehensive multi-dimensional analysis of a game project."""
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        analysis = orchestrator.analyze_game(project_id)
        return JSONResponse({"status": "success", "data": analysis.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Self-Evolution
# =============================================================================


@router.post("/orchestrator/run-learning-cycle")
async def orchestrator_run_learning_cycle():
    """Run a complete self-improvement learning cycle.

    Evolves skills, learns from recent sessions, and performs self-reflection
    to continuously improve the orchestrator's game development capabilities.
    """
    try:
        from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator
        orchestrator = get_ai_native_orchestrator()
        if not orchestrator._initialized:
            orchestrator.initialize()
        result = orchestrator.run_learning_cycle()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Phase Execution
# =============================================================================


@router.post("/orchestrator/phase/{phase_name}")
async def orchestrator_execute_phase(phase_name: str, request: Request):
    """Execute a specific development phase of the game creation pipeline.

    Valid phases: requirement_analysis, concept_design, blueprint_generation,
    architecture_design, world_building, mechanic_implementation, code_generation,
    asset_creation, level_design, narrative_generation, integration, playtesting,
    balancing, optimization, polishing, deployment, post_launch
    """
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


# =============================================================================
# Session Management
# =============================================================================


@router.get("/orchestrator/sessions")
async def orchestrator_list_sessions():
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


@router.get("/orchestrator/session/{session_id}")
async def orchestrator_get_session(session_id: str):
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


# =============================================================================
# Auto-Optimization
# =============================================================================


@router.post("/orchestrator/auto-optimize/{project_id}")
async def orchestrator_auto_optimize(project_id: str):
    """Auto-optimize a game project by running playtesting and applying optimizations."""
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