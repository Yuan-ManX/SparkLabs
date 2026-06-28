"""
SparkLabs Backend - Agent Game Forge API Routes

REST API endpoints for the Agent Game Forge system.
Provides API for game creation, playtesting, and deployment.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


# ============================================================
# Game Forge Status
# ============================================================


@router.get("/game-forge/status")
async def game_forge_status():
    """Get the Agent Game Forge system status."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        return JSONResponse({"status": "success", "data": forge.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-forge/initialize")
async def game_forge_initialize():
    """Initialize the Agent Game Forge."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        forge.initialize()
        return JSONResponse({"status": "success", "data": {"initialized": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ============================================================
# Game Creation
# ============================================================


@router.post("/game-forge/create-game")
async def game_forge_create_game(request: Request):
    """Create a complete game from a natural language description."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        from sparkai.agent.agent_game_forge import DesignFidelity, CodeQuality, AssetStyle
        body = await request.json()
        prompt = body.get("prompt", "")
        fidelity = body.get("fidelity", "detailed")
        quality = body.get("quality", "playable")
        style = body.get("style", "flat_2d")
        difficulty = body.get("difficulty", "normal")

        fidelity_map = {
            "concept": DesignFidelity.CONCEPT,
            "sketch": DesignFidelity.SKETCH,
            "detailed": DesignFidelity.DETAILED,
            "production": DesignFidelity.PRODUCTION,
        }
        quality_map = {
            "prototype": CodeQuality.PROTOTYPE,
            "playable": CodeQuality.PLAYABLE,
            "polished": CodeQuality.POLISHED,
            "production": CodeQuality.PRODUCTION,
        }
        style_map = {
            "pixel_art": AssetStyle.PIXEL_ART,
            "flat_2d": AssetStyle.FLAT_2D,
            "cartoon": AssetStyle.CARTOON,
            "realistic": AssetStyle.REALISTIC,
            "low_poly": AssetStyle.LOW_POLY,
            "voxel": AssetStyle.VOXEL,
            "stylized": AssetStyle.STYLIZED,
            "minimalist": AssetStyle.MINIMALIST,
        }

        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        project = forge.create_game(
            prompt=prompt,
            fidelity=fidelity_map.get(fidelity, DesignFidelity.DETAILED),
            quality=quality_map.get(quality, CodeQuality.PLAYABLE),
            style=style_map.get(style, AssetStyle.FLAT_2D),
            difficulty=difficulty,
        )
        return JSONResponse({"status": "success", "data": project.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ============================================================
# Project Management
# ============================================================


@router.get("/game-forge/projects")
async def game_forge_list_projects():
    """List all game forge projects."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        return JSONResponse({"status": "success", "data": forge.list_projects()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-forge/projects/{project_id}")
async def game_forge_get_project(project_id: str):
    """Get a specific game forge project."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        project = forge.get_project(project_id)
        if not project:
            return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": project.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/game-forge/projects/{project_id}")
async def game_forge_delete_project(project_id: str):
    """Delete a game forge project."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        deleted = forge.delete_project(project_id)
        if not deleted:
            return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": {"deleted": True, "project_id": project_id}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ============================================================
# Code & Assets
# ============================================================


@router.get("/game-forge/projects/{project_id}/code")
async def game_forge_get_code(project_id: str):
    """Get all code modules for a project."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        code = forge.get_code_for_project(project_id)
        if not code:
            return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": code})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-forge/projects/{project_id}/assets")
async def game_forge_get_assets(project_id: str):
    """Get all asset specifications for a project."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        assets = forge.get_assets_for_project(project_id)
        if not assets:
            return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": assets})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ============================================================
# Playtest & Iteration
# ============================================================


@router.post("/game-forge/projects/{project_id}/playtest")
async def game_forge_playtest(project_id: str):
    """Run playtest simulation on a project."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        report = forge.playtest(project_id)
        return JSONResponse({"status": "success", "data": report.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-forge/projects/{project_id}/iterate")
async def game_forge_iterate(project_id: str, request: Request):
    """Iterate on a project based on feedback."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge
        body = await request.json()
        feedback = body.get("feedback", "")
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        project = forge.iterate(project_id, feedback)
        return JSONResponse({"status": "success", "data": project.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ============================================================
# Deployment
# ============================================================


@router.post("/game-forge/projects/{project_id}/deploy")
async def game_forge_deploy(project_id: str, request: Request):
    """Deploy a project to a target platform."""
    try:
        from sparkai.agent.agent_game_forge import get_agent_game_forge, Platform
        body = await request.json()
        platform_name = body.get("platform", "web")
        platform_map = {
            "web": Platform.WEB,
            "desktop": Platform.DESKTOP,
            "mobile": Platform.MOBILE,
            "console": Platform.CONSOLE,
        }
        forge = get_agent_game_forge()
        if not forge._initialized:
            forge.initialize()
        result = forge.deploy(project_id, platform_map.get(platform_name, Platform.WEB))
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ============================================================
# Visual Composer
# ============================================================


@router.get("/visual-composer/status")
async def visual_composer_status():
    """Get the Visual Composer system status."""
    try:
        from sparkai.engine.engine_visual_composer import get_visual_composer
        composer = get_visual_composer()
        return JSONResponse({"status": "success", "data": composer.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-composer/scenes")
async def visual_composer_create_scene(request: Request):
    """Create a new visual scene."""
    try:
        from sparkai.engine.engine_visual_composer import get_visual_composer
        body = await request.json()
        name = body.get("name", "New Scene")
        width = body.get("width", 1920)
        height = body.get("height", 1080)
        composer = get_visual_composer()
        scene = composer.create_scene(name, width, height)
        return JSONResponse({"status": "success", "data": scene.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/visual-composer/scenes")
async def visual_composer_list_scenes():
    """List all visual scenes."""
    try:
        from sparkai.engine.engine_visual_composer import get_visual_composer
        composer = get_visual_composer()
        scenes = composer.list_scenes()
        return JSONResponse({"status": "success", "data": scenes})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/visual-composer/scenes/{scene_id}")
async def visual_composer_get_scene(scene_id: str):
    """Get a specific visual scene."""
    try:
        from sparkai.engine.engine_visual_composer import get_visual_composer
        composer = get_visual_composer()
        scene = composer.get_scene(scene_id)
        if not scene:
            return JSONResponse({"status": "error", "message": "Scene not found"}, status_code=404)
        return JSONResponse({"status": "success", "data": scene.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-composer/scenes/{scene_id}/layers")
async def visual_composer_add_layer(scene_id: str, request: Request):
    """Add a layer to a scene."""
    try:
        from sparkai.engine.engine_visual_composer import get_visual_composer
        body = await request.json()
        name = body.get("name", "New Layer")
        z_order = body.get("z_order", 0)
        composer = get_visual_composer()
        layer = composer.add_layer(scene_id, name, z_order)
        return JSONResponse({"status": "success", "data": layer.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-composer/scenes/{scene_id}/objects")
async def visual_composer_place_object(scene_id: str, request: Request):
    """Place an object in a scene."""
    try:
        from sparkai.engine.engine_visual_composer import get_visual_composer
        body = await request.json()
        template_id = body.get("template_id", "")
        x = body.get("x", 0)
        y = body.get("y", 0)
        layer_id = body.get("layer_id", "")
        composer = get_visual_composer()
        obj = composer.place_object(scene_id, template_id, x, y, layer_id)
        return JSONResponse({"status": "success", "data": obj.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/visual-composer/scenes/{scene_id}/save")
async def visual_composer_save_scene(scene_id: str):
    """Save a scene to serialized format."""
    try:
        from sparkai.engine.engine_visual_composer import get_visual_composer
        composer = get_visual_composer()
        data = composer.save_scene(scene_id)
        return JSONResponse({"status": "success", "data": data})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ============================================================
# Game Playground
# ============================================================


@router.get("/game-playground/status")
async def game_playground_status():
    """Get the Game Playground system status."""
    try:
        from sparkai.engine.engine_game_playground import get_game_playground
        playground = get_game_playground()
        return JSONResponse({"status": "success", "data": playground.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-playground/sessions")
async def game_playground_create_session(request: Request):
    """Create a new playground session."""
    try:
        from sparkai.engine.engine_game_playground import get_game_playground
        body = await request.json()
        scene_data = body.get("scene_data", {})
        playground = get_game_playground()
        session = playground.create_session(scene_data)
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-playground/sessions/{session_id}/start")
async def game_playground_start_session(session_id: str):
    """Start a playground session."""
    try:
        from sparkai.engine.engine_game_playground import get_game_playground
        playground = get_game_playground()
        session = playground.start_session(session_id)
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-playground/sessions/{session_id}/pause")
async def game_playground_pause_session(session_id: str):
    """Pause a playground session."""
    try:
        from sparkai.engine.engine_game_playground import get_game_playground
        playground = get_game_playground()
        session = playground.pause_session(session_id)
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-playground/sessions/{session_id}/stop")
async def game_playground_stop_session(session_id: str):
    """Stop a playground session."""
    try:
        from sparkai.engine.engine_game_playground import get_game_playground
        playground = get_game_playground()
        session = playground.stop_session(session_id)
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-playground/sessions/{session_id}/performance")
async def game_playground_performance(session_id: str):
    """Get performance metrics for a session."""
    try:
        from sparkai.engine.engine_game_playground import get_game_playground
        playground = get_game_playground()
        metrics = playground.get_performance(session_id)
        return JSONResponse({"status": "success", "data": metrics.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-playground/sessions/{session_id}/debug")
async def game_playground_debug_info(session_id: str):
    """Get debug information for a session."""
    try:
        from sparkai.engine.engine_game_playground import get_game_playground
        playground = get_game_playground()
        info = playground.get_debug_info(session_id)
        return JSONResponse({"status": "success", "data": info.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)