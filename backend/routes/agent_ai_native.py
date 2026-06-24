"""
SparkLabs Backend - AI-Native Engine Core Routes

API endpoints for the AI-native engine core, providing agent-accessible
interfaces for engine control, state observation, game creation, and
performance optimization.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# ── Request Models ──

class InitializeEngineRequest(BaseModel):
    mode: str = "design"
    profile: Optional[Dict[str, Any]] = None


class ExecuteCommandRequest(BaseModel):
    command: str
    params: Optional[Dict[str, Any]] = None


class CreateGameRequest(BaseModel):
    name: str
    genre: str = "platformer"
    visual_style: str = "2d_pixel"
    target_platform: str = "web"
    scene_count: int = 1
    entity_count: int = 10
    core_mechanics: List[str] = []
    features: List[str] = []
    physics_enabled: bool = True
    audio_enabled: bool = True
    ai_enabled: bool = True
    multiplayer: bool = False
    description: str = ""
    custom_config: Optional[Dict[str, Any]] = None


class SpawnEntityRequest(BaseModel):
    name: str
    category: str = "custom"
    position: Optional[Dict[str, float]] = None
    rotation: Optional[Dict[str, float]] = None
    scale: Optional[Dict[str, float]] = None
    components: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class SetComponentRequest(BaseModel):
    entity_id: str
    component_name: str
    component_data: Dict[str, Any] = {}


class ApplyProfileRequest(BaseModel):
    target_fps: int = 60
    quality_level: str = "balanced"
    enable_adaptive_rendering: bool = True
    enable_lod: bool = True
    enable_occlusion_culling: bool = True
    enable_batch_rendering: bool = True
    physics_quality: str = "medium"
    particle_limit: int = 1000
    custom_settings: Optional[Dict[str, Any]] = None


# ── Engine Initialization ──

@router.post("/ai-native/initialize")
async def initialize_ai_native_engine(request: InitializeEngineRequest):
    """Initialize the AI-native engine core."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        result = engine.initialize({"mode": request.mode, "profile": request.profile})
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/start")
async def start_ai_native_engine(mode: Optional[str] = None):
    """Start the AI-native engine in the specified mode."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineMode
        engine = AINativeEngineCore.get_instance()
        engine_mode = EngineMode(mode) if mode else None
        result = engine.start(engine_mode)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/stop")
async def stop_ai_native_engine():
    """Stop the AI-native engine."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        result = engine.stop()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/ai-native/status")
async def get_ai_native_engine_status():
    """Get the current status of the AI-native engine."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        result = engine.get_status()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── Command Execution ──

@router.post("/ai-native/command")
async def execute_engine_command(request: ExecuteCommandRequest):
    """Execute a command on the AI-native engine."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        if not engine._initialized:
            engine.initialize()
        command = EngineCommand(request.command)
        result = engine.execute_command(command, request.params)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except ValueError as e:
        return JSONResponse(
            {"status": "error", "message": f"Invalid command: {str(e)}"},
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/ai-native/command-history")
async def get_command_history(limit: int = 50):
    """Get the command execution history."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        result = engine.get_command_history(limit)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── State & Events ──

@router.get("/ai-native/state")
async def get_engine_state():
    """Get a complete snapshot of the engine state."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        if not engine._initialized:
            engine.initialize()
        snapshot = engine.get_state_snapshot()
        return JSONResponse({"status": "success", "data": snapshot.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/ai-native/events")
async def get_engine_events(event_type: Optional[str] = None, limit: int = 50):
    """Get engine event history."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineEventType
        engine = AINativeEngineCore.get_instance()
        et = EngineEventType(event_type) if event_type else None
        result = engine.get_event_history(et, limit)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── Entity Management ──

@router.post("/ai-native/entity/spawn")
async def spawn_entity(request: SpawnEntityRequest):
    """Spawn a new entity in the engine."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        if not engine._initialized:
            engine.initialize()
        params = {
            "name": request.name,
            "category": request.category,
            "position": request.position or {"x": 0, "y": 0, "z": 0},
            "rotation": request.rotation or {"x": 0, "y": 0, "z": 0},
            "scale": request.scale or {"x": 1, "y": 1, "z": 1},
            "components": request.components or {},
            "tags": request.tags or [],
        }
        result = engine.execute_command(EngineCommand.SPAWN_ENTITY, params)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.delete("/ai-native/entity/{entity_id}")
async def destroy_entity(entity_id: str):
    """Destroy an entity in the engine."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.DESTROY_ENTITY, {"entity_id": entity_id})
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/entity/component")
async def set_entity_component(request: SetComponentRequest):
    """Set a component on an entity."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.SET_COMPONENT, {
            "entity_id": request.entity_id,
            "component_name": request.component_name,
            "component_data": request.component_data,
        })
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/ai-native/entities")
async def get_entities(category: Optional[str] = None):
    """Get all entities, optionally filtered by category."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EntityCategory
        engine = AINativeEngineCore.get_instance()
        cat = EntityCategory(category) if category else None
        result = engine.get_entities(cat)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── Scene Management ──

@router.post("/ai-native/scene/create")
async def create_scene(name: str, config: Optional[Dict[str, Any]] = None):
    """Create a new scene."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        if not engine._initialized:
            engine.initialize()
        result = engine.execute_command(EngineCommand.CREATE_SCENE, {
            "name": name, "config": config or {},
        })
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/scene/load")
async def load_scene(scene_id: str):
    """Load a scene."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.LOAD_SCENE, {"scene_id": scene_id})
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/ai-native/scenes")
async def get_scenes():
    """Get all scenes."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        result = engine.get_scenes()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── Game Creation ──

@router.post("/ai-native/game/create")
async def create_game(request: CreateGameRequest):
    """Create a complete game from specification."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, GameCreationSpec
        engine = AINativeEngineCore.get_instance()
        if not engine._initialized:
            engine.initialize()
        spec = GameCreationSpec(
            name=request.name,
            genre=request.genre,
            visual_style=request.visual_style,
            target_platform=request.target_platform,
            scene_count=request.scene_count,
            entity_count=request.entity_count,
            core_mechanics=request.core_mechanics,
            features=request.features,
            physics_enabled=request.physics_enabled,
            audio_enabled=request.audio_enabled,
            ai_enabled=request.ai_enabled,
            multiplayer=request.multiplayer,
            description=request.description,
            custom_config=request.custom_config or {},
        )
        result = engine.create_game_from_spec(spec)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── Optimization ──

@router.get("/ai-native/optimization/profile")
async def get_optimization_profile():
    """Get the current optimization profile."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        result = engine.get_optimization_profile()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/optimization/apply")
async def apply_optimization_profile(request: ApplyProfileRequest):
    """Apply an optimization profile."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, OptimizationProfile
        engine = AINativeEngineCore.get_instance()
        profile = OptimizationProfile(
            target_fps=request.target_fps,
            quality_level=request.quality_level,
            enable_adaptive_rendering=request.enable_adaptive_rendering,
            enable_lod=request.enable_lod,
            enable_occlusion_culling=request.enable_occlusion_culling,
            enable_batch_rendering=request.enable_batch_rendering,
            physics_quality=request.physics_quality,
            particle_limit=request.particle_limit,
            custom_settings=request.custom_settings or {},
        )
        result = engine.apply_optimization_profile(profile)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/ai-native/optimization/analyze")
async def analyze_performance():
    """Analyze current performance and get optimization suggestions."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore
        engine = AINativeEngineCore.get_instance()
        result = engine.analyze_performance()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/optimization/rendering")
async def optimize_rendering(target_fps: int = 60):
    """Optimize rendering for a target FPS."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.OPTIMIZE_RENDERING, {"target_fps": target_fps})
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/optimization/physics")
async def tune_physics(gravity_scale: float = 1.0):
    """Tune physics parameters."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.TUNE_PHYSICS, {"gravity_scale": gravity_scale})
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── World Generation ──

@router.post("/ai-native/generate/terrain")
async def generate_terrain(width: int = 256, height: int = 256, seed: int = 42, algorithm: str = "perlin"):
    """Generate procedural terrain."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.GENERATE_TERRAIN, {
            "width": width, "height": height, "seed": seed, "algorithm": algorithm,
        })
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/generate/world")
async def generate_world(name: str = "New World", biome_count: int = 5, structure_count: int = 10, seed: int = 42):
    """Generate a procedural world."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.GENERATE_WORLD, {
            "name": name, "biome_count": biome_count, "structure_count": structure_count, "seed": seed,
        })
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── Simulation ──

@router.post("/ai-native/simulate")
async def simulate_ticks(num_ticks: int = 1):
    """Simulate engine ticks."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.SIMULATE_TICK, {"num_ticks": num_ticks})
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/ai-native/simulate/reset")
async def reset_simulation():
    """Reset the simulation."""
    try:
        from sparkai.engine.engine_ai_native_core import AINativeEngineCore, EngineCommand
        engine = AINativeEngineCore.get_instance()
        result = engine.execute_command(EngineCommand.RESET_SIMULATION)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# ── Agent Unified Hub Routes ──

@router.post("/hub/initialize")
async def initialize_agent_hub(mode: str = "orchestration"):
    """Initialize the agent unified hub."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub
        hub = AgentUnifiedHub.get_instance()
        result = hub.initialize({"mode": mode})
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/hub/status")
async def get_agent_hub_status():
    """Get the agent hub status."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub
        hub = AgentUnifiedHub.get_instance()
        result = hub.get_status()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/hub/task")
async def submit_hub_task(task_type: str, description: str, priority: int = 0):
    """Submit a task to the agent hub."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub, TaskType
        hub = AgentUnifiedHub.get_instance()
        if not hub._initialized:
            hub.initialize()
        tt = TaskType(task_type)
        task = hub.submit_task(tt, description, priority)
        return JSONResponse({"status": "success", "data": task.to_dict()})
    except ValueError as e:
        return JSONResponse(
            {"status": "error", "message": f"Invalid task type: {str(e)}"},
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/hub/tasks")
async def get_hub_tasks():
    """Get active tasks."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub
        hub = AgentUnifiedHub.get_instance()
        result = hub.get_active_tasks()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/hub/tasks/history")
async def get_hub_task_history(task_type: Optional[str] = None, limit: int = 50):
    """Get task history."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub, TaskType
        hub = AgentUnifiedHub.get_instance()
        tt = TaskType(task_type) if task_type else None
        result = hub.get_task_history(tt, limit)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/hub/game/create")
async def create_game_via_hub(name: str, genre: str = "platformer"):
    """Create a game via the agent hub."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub
        hub = AgentUnifiedHub.get_instance()
        if not hub._initialized:
            hub.initialize()
        result = hub.create_game(name, genre)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/hub/events")
async def get_hub_events(event_type: Optional[str] = None, limit: int = 50):
    """Get hub event history."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub, HubEventType
        hub = AgentUnifiedHub.get_instance()
        et = HubEventType(event_type) if event_type else None
        result = hub.get_event_history(et, limit)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/hub/stats")
async def get_hub_stats():
    """Get accumulated hub statistics."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub
        hub = AgentUnifiedHub.get_instance()
        result = hub.get_stats()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/hub/shutdown")
async def shutdown_agent_hub():
    """Shutdown the agent hub."""
    try:
        from sparkai.agent.agent_unified_hub import AgentUnifiedHub
        hub = AgentUnifiedHub.get_instance()
        result = hub.shutdown()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )