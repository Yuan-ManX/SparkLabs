"""
SparkLabs Backend - Engine Routes

API endpoints for engine control, ECS world management,
scene management, and component/system registry.
"""

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from sparkai.engine.engine import SparkEngine
from sparkai.engine.ecs.component import ComponentRegistry
from sparkai.engine.ecs.system import SystemRegistry
from sparkai.engine.ecs.components import (
    Transform, Renderable, SpriteRenderer, TextRenderer,
    PhysicsBody, Collider, Camera, AudioSource, Animator,
    InputReceiver, AIBrain, Script, Tween,
)
from sparkai.engine.ecs.systems import (
    TransformSystem, PhysicsSystem, RenderSystem,
    AnimationSystem, AudioSystem, InputSystem, AISystem,
    TweenSystem, ScriptSystem, CollisionSystem,
)

router = APIRouter()


class SceneCreateRequest(BaseModel):
    name: str = "Untitled Scene"


class WorldCreateRequest(BaseModel):
    name: str = "World"


class EntityCreateRequest(BaseModel):
    name: str = "Entity"
    components: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class ComponentAddRequest(BaseModel):
    component_type: str
    data: Optional[Dict[str, Any]] = None


class SystemAddRequest(BaseModel):
    system_type: str


# Engine control

@router.get("/status")
async def get_engine_status():
    engine = SparkEngine.get_instance()
    return engine.get_status()


@router.post("/start")
async def start_engine():
    engine = SparkEngine.get_instance()
    engine.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_engine():
    engine = SparkEngine.get_instance()
    engine.stop()
    return {"status": "stopped"}


# ECS Registry

@router.get("/ecs/component-types")
async def list_component_types():
    return {"component_types": ComponentRegistry.list_types()}


@router.get("/ecs/component-types/{type_name}/schema")
async def get_component_schema(type_name: str):
    schema = ComponentRegistry.get_schema(type_name)
    if schema:
        return {"schema": schema}
    return {"error": "Component type not found"}


@router.get("/ecs/system-types")
async def list_system_types():
    return {"system_types": SystemRegistry.list_types()}


# World management

@router.post("/worlds/create")
async def create_world(request: WorldCreateRequest):
    engine = SparkEngine.get_instance()
    world = engine.create_world(name=request.name)
    return world.get_status()


@router.get("/worlds")
async def list_worlds():
    engine = SparkEngine.get_instance()
    return {"worlds": engine.list_worlds()}


@router.get("/worlds/{world_id}")
async def get_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        return world.get_status()
    return {"error": "World not found"}


@router.get("/worlds/{world_id}/status")
async def get_world_status(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        return world.get_status()
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/start")
async def start_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.start()
        return {"status": "started"}
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/stop")
async def stop_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.stop()
        return {"status": "stopped"}
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/pause")
async def pause_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.pause()
        return {"status": "paused"}
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/resume")
async def resume_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.resume()
        return {"status": "resumed"}
    return {"error": "World not found"}


@router.delete("/worlds/{world_id}")
async def delete_world(world_id: str):
    engine = SparkEngine.get_instance()
    success = engine.delete_world(world_id)
    return {"success": success}


# Entity management within a world

@router.post("/worlds/{world_id}/entities/create")
async def create_world_entity(world_id: str, request: EntityCreateRequest):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.create_entity(name=request.name)
    if request.tags:
        for tag in request.tags:
            entity.add_tag(tag)
    if request.components:
        for comp_data in request.components:
            comp_type = comp_data.get("type", "")
            comp_params = comp_data.get("data", {})
            component = ComponentRegistry.create(comp_type, **comp_params)
            if component:
                entity.add_component(component)
    return entity.to_dict()


@router.get("/worlds/{world_id}/entities")
async def list_world_entities(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    return world.entities.to_dict()


@router.get("/worlds/{world_id}/entities/{entity_id}")
async def get_world_entity(world_id: str, entity_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.entities.get_entity(entity_id)
    if entity:
        return entity.to_dict()
    return {"error": "Entity not found"}


@router.delete("/worlds/{world_id}/entities/{entity_id}")
async def delete_world_entity(world_id: str, entity_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.destroy_entity(entity_id)
    if entity:
        return {"success": True}
    return {"error": "Entity not found"}


@router.post("/worlds/{world_id}/entities/{entity_id}/components")
async def add_entity_component(world_id: str, entity_id: str, request: ComponentAddRequest):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.entities.get_entity(entity_id)
    if not entity:
        return {"error": "Entity not found"}
    component = ComponentRegistry.create(request.component_type, **(request.data or {}))
    if component:
        entity.add_component(component)
        world.entities.on_component_added(entity_id, request.component_type)
        return component.to_dict()
    return {"error": "Component type not found"}


@router.delete("/worlds/{world_id}/entities/{entity_id}/components/{component_type}")
async def remove_entity_component(world_id: str, entity_id: str, component_type: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.entities.get_entity(entity_id)
    if not entity:
        return {"error": "Entity not found"}
    removed = entity.remove_component(component_type)
    if removed:
        world.entities.on_component_removed(entity_id, component_type)
        return {"success": True}
    return {"error": "Component not found"}


# System management within a world

@router.post("/worlds/{world_id}/systems/add")
async def add_world_system(world_id: str, request: SystemAddRequest):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    system_instance = SystemRegistry.create(request.system_type)
    if system_instance:
        world.add_system(system_instance)
        return system_instance.to_dict()
    return {"error": "System type not found"}


@router.get("/worlds/{world_id}/systems")
async def list_world_systems(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    return {"systems": world.systems.list_systems()}


@router.delete("/worlds/{world_id}/systems/{system_type}")
async def remove_world_system(world_id: str, system_type: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    removed = world.remove_system(system_type)
    if removed:
        return {"success": True}
    return {"error": "System not found"}


# Scene management (legacy)

@router.post("/scenes/create")
async def create_scene(request: SceneCreateRequest):
    engine = SparkEngine.get_instance()
    scene = engine.create_scene(name=request.name)
    return scene.to_dict()


@router.get("/scenes")
async def list_scenes():
    engine = SparkEngine.get_instance()
    return {"scenes": engine.list_scenes()}


@router.get("/scenes/{scene_id}")
async def get_scene(scene_id: str):
    engine = SparkEngine.get_instance()
    scene = engine.get_scene(scene_id)
    if scene:
        return scene.to_dict()
    return {"error": "Scene not found"}


@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str):
    engine = SparkEngine.get_instance()
    success = engine.delete_scene(scene_id)
    return {"success": success}


# ---------------------------------------------------------------------------
# Audio Synthesis Routes
# ---------------------------------------------------------------------------

@router.get("/audio-synthesis/stats")
async def get_audio_synthesis_stats():
    """Get audio synthesis engine statistics."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    synth = get_audio_synthesis()
    return synth.get_stats()


@router.get("/audio-synthesis/oscillators")
async def list_audio_oscillators():
    """List all oscillator configurations."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    synth = get_audio_synthesis()
    return {"oscillators": synth.list_oscillators()}


@router.post("/audio-synthesis/oscillators")
async def create_audio_oscillator(request: Request):
    """Create a new oscillator."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    body = await request.json()
    synth = get_audio_synthesis()
    osc = synth.create_oscillator(
        waveform=body.get("waveform", "sine"),
        frequency=body.get("frequency", 440.0),
        amplitude=body.get("amplitude", 0.5),
        detune_cents=body.get("detune_cents", 0.0),
    )
    return osc.to_dict()


@router.delete("/audio-synthesis/oscillators/{oscillator_id}")
async def remove_audio_oscillator(oscillator_id: str):
    """Remove an oscillator."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    synth = get_audio_synthesis()
    return {"success": synth.remove_oscillator(oscillator_id)}


@router.post("/audio-synthesis/sfx/{effect_type}")
async def synthesize_sound_effect(effect_type: str, request: Request):
    """Synthesize a sound effect. Types: laser, explosion, collect, jump, hit, powerup, ambient."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    body = await request.json()
    synth = get_audio_synthesis()

    effect_map = {
        "laser": synth.synthesize_laser,
        "explosion": synth.synthesize_explosion,
        "collect": synth.synthesize_collect,
        "jump": synth.synthesize_jump,
        "hit": synth.synthesize_hit,
        "powerup": synth.synthesize_powerup,
        "ambient": synth.synthesize_ambient,
    }

    if effect_type not in effect_map:
        return {"error": f"Unknown effect type: {effect_type}"}

    kwargs = {k: v for k, v in body.items() if k in ("frequency", "start_freq", "end_freq", "duration_ms", "amplitude", "base_freq")}
    sample = effect_map[effect_type](**kwargs)
    return sample.to_dict()


@router.post("/audio-synthesis/noise")
async def generate_noise(request: Request):
    """Generate colored noise."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    body = await request.json()
    synth = get_audio_synthesis()
    samples = synth.generate_noise(
        color=body.get("color", "white"),
        duration_ms=body.get("duration_ms", 1000.0),
        amplitude=body.get("amplitude", 0.5),
    )
    sample = synth._create_sample(samples, body.get("duration_ms", 1000.0))
    return sample.to_dict()


@router.post("/audio-synthesis/chord")
async def generate_chord(request: Request):
    """Generate a musical chord."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    body = await request.json()
    synth = get_audio_synthesis()
    sample = synth.generate_chord(
        root_note=body.get("root_note", "C4"),
        chord_type=body.get("chord_type", "major"),
        duration_ms=body.get("duration_ms", 1000.0),
        amplitude=body.get("amplitude", 0.4),
        waveform=body.get("waveform", "sine"),
    )
    return sample.to_dict()


@router.post("/audio-synthesis/melody")
async def generate_melody(request: Request):
    """Generate a random melody."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    body = await request.json()
    synth = get_audio_synthesis()
    sample = synth.generate_melody(
        scale_type=body.get("scale_type", "major"),
        root_note=body.get("root_note", "C4"),
        note_count=body.get("note_count", 8),
        note_duration_ms=body.get("note_duration_ms", 250.0),
        amplitude=body.get("amplitude", 0.4),
        waveform=body.get("waveform", "sine"),
        seed=body.get("seed"),
    )
    return sample.to_dict()


@router.post("/audio-synthesis/rhythm")
async def generate_rhythm(request: Request):
    """Generate a rhythmic pattern."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    body = await request.json()
    synth = get_audio_synthesis()
    sample = synth.generate_rhythm_pattern(
        bpm=body.get("bpm", 120.0),
        beats=body.get("beats", 8),
        hit_duration_ms=body.get("hit_duration_ms", 50.0),
        amplitude=body.get("amplitude", 0.5),
    )
    return sample.to_dict()


@router.get("/audio-synthesis/samples")
async def list_audio_samples():
    """List all generated audio samples."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    synth = get_audio_synthesis()
    return {"samples": synth.list_samples()}


@router.get("/audio-synthesis/samples/{sample_id}")
async def get_audio_sample(sample_id: str):
    """Get a specific audio sample."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    synth = get_audio_synthesis()
    sample = synth.get_sample(sample_id)
    if sample:
        return sample
    return {"error": "Sample not found"}


@router.get("/audio-synthesis/scale/{scale_type}")
async def get_scale_notes(scale_type: str, root_note: str = "C4"):
    """Get notes in a musical scale."""
    from sparkai.engine.engine_audio_synthesis import get_audio_synthesis
    synth = get_audio_synthesis()
    return {"notes": synth.get_scale_notes(root_note, scale_type)}


# ---------------------------------------------------------------------------
# Environment Manager Routes
# ---------------------------------------------------------------------------

@router.get("/environment/platform")
async def get_platform_info():
    """Get platform information."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return em.get_platform_info()


@router.get("/environment/stats")
async def get_environment_stats():
    """Get environment system statistics."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return em.get_system_stats()


@router.get("/environment/health")
async def check_environment_health():
    """Check environment health."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return em.check_health()


@router.get("/environment/profile")
async def get_environment_profile():
    """Get current environment profile."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return {"profile": em.get_profile()}


@router.post("/environment/profile")
async def set_environment_profile(request: Request):
    """Set the environment profile."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    body = await request.json()
    em = get_engine_environment_manager()
    em.set_profile(body.get("profile", "development"))
    return {"profile": em.get_profile()}


@router.get("/environment/budgets")
async def list_resource_budgets():
    """List all resource budgets."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return {"budgets": em.list_resource_budgets()}


@router.post("/environment/budgets")
async def create_resource_budget(request: Request):
    """Create a resource budget."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    body = await request.json()
    em = get_engine_environment_manager()
    budget = em.create_resource_budget(
        category=body.get("category", "general"),
        cpu_cores=body.get("cpu_cores", 1.0),
        memory_mb=body.get("memory_mb", 256.0),
        gpu_memory_mb=body.get("gpu_memory_mb", 0.0),
        priority=body.get("priority", 0),
    )
    return budget.to_dict()


@router.get("/environment/dependencies")
async def list_dependencies(subsystem: Optional[str] = None, status: Optional[str] = None):
    """List all dependencies."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return {"dependencies": em.list_dependencies(subsystem, status)}


@router.post("/environment/dependencies")
async def register_dependency(request: Request):
    """Register a new dependency."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    body = await request.json()
    em = get_engine_environment_manager()
    dep = em.register_dependency(
        name=body.get("name", ""),
        version=body.get("version", "1.0.0"),
        subsystem=body.get("subsystem", "custom"),
        dependencies=body.get("dependencies", []),
        optional=body.get("optional", False),
        metadata=body.get("metadata"),
    )
    return dep.to_dict()


@router.get("/environment/dependencies/graph")
async def get_dependency_graph():
    """Get the dependency graph."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return em.get_dependency_graph()


@router.post("/environment/subsystems/{subsystem}/initialize")
async def initialize_subsystem(subsystem: str):
    """Initialize a subsystem."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return em.initialize_subsystem(subsystem)


@router.get("/environment/subsystems")
async def list_initialized_subsystems():
    """List initialized subsystems."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return {"subsystems": em.list_initialized_subsystems()}


@router.get("/environment/sandboxes")
async def list_sandboxes(subsystem: Optional[str] = None):
    """List all sandboxes."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return {"sandboxes": em.list_sandboxes(subsystem)}


@router.post("/environment/sandboxes")
async def create_sandbox(request: Request):
    """Create a sandbox."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    body = await request.json()
    em = get_engine_environment_manager()
    sandbox = em.create_sandbox(
        subsystem=body.get("subsystem", "custom"),
        isolation_level=body.get("isolation_level", "none"),
        max_memory_mb=body.get("max_memory_mb", 512.0),
        max_cpu_time_ms=body.get("max_cpu_time_ms", 10000.0),
        allowed_paths=body.get("allowed_paths"),
        denied_paths=body.get("denied_paths"),
        network_access=body.get("network_access", False),
    )
    return sandbox.to_dict()


@router.get("/environment/snapshots")
async def list_environment_snapshots():
    """List all environment snapshots."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return {"snapshots": em.list_snapshots()}


@router.post("/environment/snapshots")
async def create_environment_snapshot():
    """Create an environment snapshot."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    snapshot = em.create_snapshot()
    return snapshot.to_dict()


@router.get("/environment/env-vars")
async def list_env_variables():
    """List all managed environment variables."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return {"variables": em.list_env_variables()}


@router.post("/environment/env-vars")
async def set_env_variable(request: Request):
    """Set an environment variable."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    body = await request.json()
    em = get_engine_environment_manager()
    em.set_env(body.get("key", ""), body.get("value", ""))
    return {"success": True}


@router.get("/environment/resource-usage")
async def get_resource_usage():
    """Get current resource usage."""
    from sparkai.engine.engine_environment_manager import get_engine_environment_manager
    em = get_engine_environment_manager()
    return em.get_resource_usage()


# ---------------------------------------------------------------------------
# Weather System Routes
# ---------------------------------------------------------------------------

@router.get("/weather/stats")
async def get_weather_stats():
    """Get weather system statistics."""
    from sparkai.engine.engine_weather_system import get_weather_system
    ws = get_weather_system()
    return ws.get_stats()


@router.post("/weather/update")
async def update_weather_simulation(request: Request):
    """Update weather simulation."""
    from sparkai.engine.engine_weather_system import get_weather_system
    body = await request.json()
    ws = get_weather_system()
    return ws.update(delta_time_ms=body.get("delta_time_ms", 1000))


@router.post("/weather/set-weather")
async def set_weather(request: Request):
    """Set weather manually for a region."""
    from sparkai.engine.engine_weather_system import get_weather_system
    body = await request.json()
    ws = get_weather_system()
    return ws.set_weather(
        region_id=body.get("region_id", ""),
        weather_type=body.get("weather_type", "rain"),
        intensity=body.get("intensity", "moderate"),
    )


@router.post("/weather/transition")
async def transition_weather(request: Request):
    """Transition weather over time."""
    from sparkai.engine.engine_weather_system import get_weather_system
    body = await request.json()
    ws = get_weather_system()
    return ws.transition(
        region_id=body.get("region_id", ""),
        target_weather=body.get("target_weather", "storm"),
        duration_ms=body.get("duration_ms", 5000),
    )


@router.post("/weather/set-climate")
async def set_climate(request: Request):
    """Set climate profile for a region."""
    from sparkai.engine.engine_weather_system import get_weather_system
    body = await request.json()
    ws = get_weather_system()
    return ws.set_climate(
        region_id=body.get("region_id", ""),
        climate_zone=body.get("climate_zone", "tropical"),
    )


@router.get("/weather/current/{region_id}")
async def get_current_weather(region_id: str):
    """Get current weather for a region."""
    from sparkai.engine.engine_weather_system import get_weather_system
    ws = get_weather_system()
    return ws.get_current(region_id)


@router.get("/weather/forecast/{region_id}")
async def get_weather_forecast(region_id: str):
    """Get weather forecast for a region."""
    from sparkai.engine.engine_weather_system import get_weather_system
    ws = get_weather_system()
    return ws.get_forecast(region_id)


@router.get("/weather/particles/{region_id}")
async def get_weather_particles(region_id: str):
    """Get active weather particles for a region."""
    from sparkai.engine.engine_weather_system import get_weather_system
    ws = get_weather_system()
    return ws.get_particles(region_id)


# ---------------------------------------------------------------------------
# Water Simulation Routes
# ---------------------------------------------------------------------------

@router.get("/water/stats")
async def get_water_stats():
    """Get water simulation statistics."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    ws = get_water_simulation()
    return ws.get_stats()


@router.post("/water/create-body")
async def create_water_body(request: Request):
    """Create a water body."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    body = await request.json()
    ws = get_water_simulation()
    return ws.create_body(
        name=body.get("name", ""),
        body_type=body.get("body_type", "rectangular"),
        x=body.get("x", 0),
        y=body.get("y", 0),
        width=body.get("width", 100),
        height=body.get("height", 50),
    )


@router.post("/water/update")
async def update_water_simulation(request: Request):
    """Update water simulation."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    body = await request.json()
    ws = get_water_simulation()
    return ws.update(delta_time_ms=body.get("delta_time_ms", 16))


@router.get("/water/bodies")
async def list_water_bodies():
    """List all water bodies."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    ws = get_water_simulation()
    return ws.list_bodies()


@router.post("/water/add-object")
async def add_buoyant_object(request: Request):
    """Add a buoyant object to a water body."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    body = await request.json()
    ws = get_water_simulation()
    return ws.add_object(
        water_body_id=body.get("water_body_id", ""),
        name=body.get("name", ""),
        x=body.get("x", 50),
        y=body.get("y", 30),
        width=body.get("width", 10),
        height=body.get("height", 10),
        mass=body.get("mass", 5),
    )


@router.post("/water/set-waves")
async def set_wave_parameters(request: Request):
    """Set wave parameters for a water body."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    body = await request.json()
    ws = get_water_simulation()
    return ws.set_waves(
        water_body_id=body.get("water_body_id", ""),
        amplitude=body.get("amplitude", 2.0),
        frequency=body.get("frequency", 0.5),
        speed=body.get("speed", 1.0),
    )


@router.post("/water/splash")
async def generate_splash(request: Request):
    """Generate a splash effect."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    body = await request.json()
    ws = get_water_simulation()
    return ws.splash(
        water_body_id=body.get("water_body_id", ""),
        x=body.get("x", 50),
        y=body.get("y", 25),
        velocity=body.get("velocity", 5.0),
        splash_type=body.get("splash_type", "entry"),
    )


@router.get("/water/surface/{water_body_id}")
async def get_water_surface(water_body_id: str):
    """Get surface points for a water body."""
    from sparkai.engine.engine_water_simulation import get_water_simulation
    ws = get_water_simulation()
    return ws.get_surface(water_body_id)


# ---------------------------------------------------------------------------
# Engine Unification Core Routes
# ---------------------------------------------------------------------------

@router.get("/unification-core/status")
async def get_unification_core_status():
    """Get Engine Unification Core status for all orchestrators."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    core = get_engine_unification_core()
    return core.get_status()

@router.get("/unification-core/report")
async def get_unification_core_report():
    """Get comprehensive engine diagnostics report."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    core = get_engine_unification_core()
    return core.get_engine_report()

@router.post("/unification-core/initialize")
async def initialize_unification_core(request: Request):
    """Initialize engine unification subsystems."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    body = await request.json()
    core = get_engine_unification_core()
    return core.initialize(subsystems=body.get("subsystems"))

@router.post("/unification-core/tick")
async def tick_unification_core(request: Request):
    """Execute one unified game loop tick."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    body = await request.json()
    core = get_engine_unification_core()
    return core.tick(delta_time=body.get("delta_time", 0.016))

@router.post("/unification-core/render")
async def render_unification_core():
    """Execute coordinated render pipeline."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    core = get_engine_unification_core()
    return core.render_frame()

@router.post("/unification-core/shutdown")
async def shutdown_unification_core():
    """Gracefully shutdown engine subsystems."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    core = get_engine_unification_core()
    core.shutdown()
    return {"status": "shutdown"}

@router.get("/unification-core/subsystems")
async def list_unification_subsystems():
    """List all engine subsystems by orchestrator."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    core = get_engine_unification_core()
    return {"subsystems": core.list_subsystems()}

@router.post("/unification-core/target-fps")
async def set_unification_target_fps(request: Request):
    """Set target FPS for engine."""
    from sparkai.engine.engine_unification_core import get_engine_unification_core
    body = await request.json()
    core = get_engine_unification_core()
    core.set_target_fps(body.get("fps", 60))
    return {"target_fps": body.get("fps", 60)}

# ---------------------------------------------------------------------------
# Volumetric Rendering Routes
# ---------------------------------------------------------------------------

@router.get("/volumetric-rendering/status")
async def get_volumetric_rendering_status():
    """Get volumetric rendering system status."""
    from sparkai.engine.engine_volumetric_rendering import get_volumetric_rendering
    vr = get_volumetric_rendering()
    return vr.get_status()


@router.post("/volumetric-rendering/ray-march")
async def volumetric_ray_march(request: Request):
    """Perform ray marching through participating media."""
    from sparkai.engine.engine_volumetric_rendering import get_volumetric_rendering
    body = await request.json()
    vr = get_volumetric_rendering()
    result = vr.ray_march(
        camera_pos=tuple(body.get("camera_pos", [0, 0])),
        ray_direction=tuple(body.get("ray_direction", [0, 1])),
        max_distance=body.get("max_distance", 100.0),
        step_count=body.get("step_count", 64),
    )
    return result.to_dict()


@router.post("/volumetric-rendering/fog-config")
async def create_fog_config(request: Request):
    """Create a volumetric fog configuration."""
    from sparkai.engine.engine_volumetric_rendering import get_volumetric_rendering
    body = await request.json()
    vr = get_volumetric_rendering()
    config = vr.create_fog_config(
        name=body.get("name", ""),
        density=body.get("density", 0.01),
        scattering_coefficient=body.get("scattering_coefficient", 0.5),
        absorption_coefficient=body.get("absorption_coefficient", 0.1),
        phase_g=body.get("phase_g", 0.0),
        color=tuple(body.get("color", [0.5, 0.6, 0.7, 1.0])),
    )
    return config.to_dict()


@router.post("/volumetric-rendering/light-config")
async def create_volumetric_light_config(request: Request):
    """Create a volumetric light configuration."""
    from sparkai.engine.engine_volumetric_rendering import get_volumetric_rendering
    body = await request.json()
    vr = get_volumetric_rendering()
    config = vr.create_light_config(
        name=body.get("name", ""),
        position=tuple(body.get("position", [0, 0])),
        intensity=body.get("intensity", 1.0),
        color=tuple(body.get("color", [1.0, 1.0, 1.0])),
        radius=body.get("radius", 10.0),
        volumetric_enabled=body.get("volumetric_enabled", True),
    )
    return config.to_dict()


@router.post("/volumetric-rendering/cloud-config")
async def create_cloud_config(request: Request):
    """Create a volumetric cloud configuration."""
    from sparkai.engine.engine_volumetric_rendering import get_volumetric_rendering
    body = await request.json()
    vr = get_volumetric_rendering()
    config = vr.create_cloud_config(
        name=body.get("name", ""),
        coverage=body.get("coverage", 0.5),
        density=body.get("density", 0.3),
        altitude=body.get("altitude", 100.0),
        thickness=body.get("thickness", 20.0),
        wind_speed=body.get("wind_speed", 1.0),
        wind_direction=body.get("wind_direction", 0.0),
    )
    return config.to_dict()


@router.post("/volumetric-rendering/phase-function")
async def evaluate_phase_function(request: Request):
    """Evaluate a scattering phase function."""
    from sparkai.engine.engine_volumetric_rendering import get_volumetric_rendering
    body = await request.json()
    vr = get_volumetric_rendering()
    result = vr.evaluate_phase_function(
        scattering_model=body.get("scattering_model", "rayleigh"),
        cos_theta=body.get("cos_theta", 0.0),
        g=body.get("g", 0.0),
    )
    return {"result": result}


@router.post("/volumetric-rendering/quality-preset")
async def set_quality_preset(request: Request):
    """Set the volumetric rendering quality preset."""
    from sparkai.engine.engine_volumetric_rendering import get_volumetric_rendering, QualityPreset
    body = await request.json()
    vr = get_volumetric_rendering()
    preset_str = body.get("preset", "medium")
    try:
        preset = QualityPreset(preset_str)
    except ValueError:
        preset = QualityPreset.MEDIUM
    result = vr.set_quality_preset(preset)
    return {"quality_preset": preset.value, "settings": result}

# ---------------------------------------------------------------------------
# Crowd Dynamics Routes
# ---------------------------------------------------------------------------

@router.get("/crowd-dynamics/status")
async def get_crowd_dynamics_status():
    """Get crowd dynamics system status."""
    from sparkai.engine.engine_crowd_dynamics import get_crowd_dynamics
    cd = get_crowd_dynamics()
    return cd.get_status()


@router.post("/crowd-dynamics/create-agent")
async def create_crowd_agent(request: Request):
    """Create a crowd agent."""
    from sparkai.engine.engine_crowd_dynamics import get_crowd_dynamics
    body = await request.json()
    cd = get_crowd_dynamics()
    agent = cd.create_agent(
        name=body.get("name", ""),
        position=tuple(body.get("position", [0, 0])),
        velocity=tuple(body.get("velocity", [0, 0])),
        max_speed=body.get("max_speed", 5.0),
        preferred_speed=body.get("preferred_speed", 3.0),
        radius=body.get("radius", 0.5),
        group_id=body.get("group_id"),
        behavior=body.get("behavior", "flocking"),
    )
    return agent.to_dict()


@router.post("/crowd-dynamics/create-group")
async def create_crowd_group(request: Request):
    """Create a crowd group."""
    from sparkai.engine.engine_crowd_dynamics import get_crowd_dynamics
    body = await request.json()
    cd = get_crowd_dynamics()
    group = cd.create_group(
        name=body.get("name", ""),
        cohesion_weight=body.get("cohesion_weight", 0.3),
        alignment_weight=body.get("alignment_weight", 0.3),
        separation_weight=body.get("separation_weight", 0.4),
        formation=body.get("formation", "none"),
    )
    return group.to_dict()


@router.post("/crowd-dynamics/update")
async def update_crowd_simulation(request: Request):
    """Update the crowd simulation."""
    from sparkai.engine.engine_crowd_dynamics import get_crowd_dynamics
    body = await request.json()
    cd = get_crowd_dynamics()
    agents = cd.update(
        delta_time=body.get("delta_time", 0.016),
        max_agents=body.get("max_agents", 1000),
    )
    return {"agents": [a.to_dict() for a in agents], "count": len(agents)}


@router.post("/crowd-dynamics/create-flow-field")
async def create_flow_field(request: Request):
    """Create a flow field for crowd navigation."""
    from sparkai.engine.engine_crowd_dynamics import get_crowd_dynamics
    body = await request.json()
    cd = get_crowd_dynamics()
    field = cd.create_flow_field(
        name=body.get("name", ""),
        resolution=tuple(body.get("resolution", [10, 10])),
        field_data=body.get("field_data"),
    )
    return field.to_dict()


@router.post("/crowd-dynamics/create-obstacle")
async def create_crowd_obstacle(request: Request):
    """Add an obstacle to the crowd simulation."""
    from sparkai.engine.engine_crowd_dynamics import get_crowd_dynamics
    body = await request.json()
    cd = get_crowd_dynamics()
    cd.add_obstacle(
        x=body.get("x", 0),
        y=body.get("y", 0),
        width=body.get("width", 1),
        height=body.get("height", 1),
    )
    return {"success": True}


@router.post("/crowd-dynamics/density-map")
async def compute_density_map(request: Request):
    """Compute the crowd density map."""
    from sparkai.engine.engine_crowd_dynamics import get_crowd_dynamics
    body = await request.json()
    cd = get_crowd_dynamics()
    density = cd.compute_density_map(grid_size=body.get("grid_size"))
    return {"density_map": density}

# ---------------------------------------------------------------------------
# Fluid Dynamics Routes
# ---------------------------------------------------------------------------

@router.get("/fluid-dynamics/status")
async def get_fluid_dynamics_status():
    """Get fluid dynamics system status."""
    from sparkai.engine.engine_fluid_dynamics import get_fluid_dynamics
    fd = get_fluid_dynamics()
    return fd.get_status()


@router.post("/fluid-dynamics/create-simulation")
async def create_fluid_simulation(request: Request):
    """Create a fluid simulation."""
    from sparkai.engine.engine_fluid_dynamics import get_fluid_dynamics, FluidConfig
    body = await request.json()
    fd = get_fluid_dynamics()
    config = FluidConfig(
        rest_density=body.get("rest_density", 1000.0),
        gas_constant=body.get("gas_constant", 2000.0),
        viscosity_coefficient=body.get("viscosity_coefficient", 0.01),
        surface_tension_coefficient=body.get("surface_tension_coefficient", 0.05),
        kernel_radius=body.get("kernel_radius", 0.1),
        gravity=tuple(body.get("gravity", [0, -9.81])),
    )
    sim = fd.create_simulation(
        config=config,
        bounds=(-10, -10, 10, 10),
    )
    return sim.to_dict()


@router.post("/fluid-dynamics/add-particles")
async def add_fluid_particles(request: Request):
    """Add particles to a fluid simulation."""
    from sparkai.engine.engine_fluid_dynamics import get_fluid_dynamics
    body = await request.json()
    fd = get_fluid_dynamics()
    particles = fd.add_particles(
        simulation_id=body.get("simulation_id", ""),
        particle_count=body.get("particle_count", 100),
        region=body.get("region", {"x": 0, "y": 0, "width": 1, "height": 1}),
        velocity_range=body.get("velocity_range"),
        mass=body.get("mass", 0.001),
    )
    return {"particles": [p.to_dict() for p in particles], "count": len(particles)}


@router.post("/fluid-dynamics/step")
async def step_fluid_simulation(request: Request):
    """Advance the fluid simulation."""
    from sparkai.engine.engine_fluid_dynamics import get_fluid_dynamics
    body = await request.json()
    fd = get_fluid_dynamics()
    stats = fd.step_simulation(
        simulation_id=body.get("simulation_id", ""),
        delta_time=body.get("delta_time", 0.016),
        max_iterations=body.get("max_iterations", 8),
    )
    return stats.to_dict()


@router.post("/fluid-dynamics/create-boundary")
async def create_fluid_boundary(request: Request):
    """Create a fluid boundary."""
    from sparkai.engine.engine_fluid_dynamics import get_fluid_dynamics
    body = await request.json()
    fd = get_fluid_dynamics()
    boundary = fd.create_boundary(
        simulation_id=body.get("simulation_id", ""),
        boundary_type=body.get("boundary_type", "wall"),
        params=body.get("params", {}),
    )
    return boundary.to_dict()


@router.get("/fluid-dynamics/simulations")
async def list_fluid_simulations():
    """List all fluid simulations."""
    from sparkai.engine.engine_fluid_dynamics import get_fluid_dynamics
    fd = get_fluid_dynamics()
    return {"simulations": fd.list_simulations()}


@router.post("/fluid-dynamics/neighbor-search")
async def fluid_neighbor_search(request: Request):
    """Perform neighbor search for particles."""
    from sparkai.engine.engine_fluid_dynamics import get_fluid_dynamics
    body = await request.json()
    fd = get_fluid_dynamics()
    simulation = fd._simulations.get(body.get("simulation_id", ""))
    if not simulation:
        return {"error": "Simulation not found"}
    particle_id = body.get("particle_id", "")
    radius = body.get("radius", 0.1)
    all_particles = list(simulation.particles.values())
    neighbor_map = fd.neighbor_search(all_particles, radius)
    neighbors = neighbor_map.get(particle_id, [])
    return {"neighbors": neighbors, "count": len(neighbors)}

# ---------------------------------------------------------------------------
# Procedural Animation Routes
# ---------------------------------------------------------------------------

@router.get("/procedural-animation/status")
async def procedural_animation_status():
    """Get procedural animation system status."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    pa = get_procedural_animation()
    return pa.get_status()


@router.post("/procedural-animation/create-skeleton")
async def create_animation_skeleton(request: Request):
    """Create a skeleton from bone hierarchy data."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    body = await request.json()
    pa = get_procedural_animation()
    skeleton = pa.create_skeleton(
        name=body.get("name", ""),
        bones_data=body.get("bones_data", []),
    )
    return skeleton.to_dict()


@router.post("/procedural-animation/add-ik")
async def add_ik_chain(request: Request):
    """Add an IK solver chain."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    body = await request.json()
    pa = get_procedural_animation()
    chain = body.get("chain", [])
    if isinstance(chain, str):
        chain = [b.strip() for b in chain.split(",") if b.strip()]
    target = body.get("target", [0, 0, 0])
    if isinstance(target, list):
        target = tuple(target)
    ik = pa.add_ik_chain(
        skeleton_id=body.get("skeleton_id", ""),
        chain=chain,
        target=target,
        method=body.get("method", "fabrik"),
        iterations=body.get("iterations", 10),
        tolerance=body.get("tolerance", 0.001),
    )
    return ik.to_dict()


@router.post("/procedural-animation/solve-ik")
async def solve_ik_chain(request: Request):
    """Solve IK and update bone positions."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    body = await request.json()
    pa = get_procedural_animation()
    skeleton = pa.solve_ik(
        skeleton_id=body.get("skeleton_id", ""),
        ik_target_id=body.get("ik_target_id", ""),
        max_iterations=body.get("max_iterations", 50),
    )
    return skeleton.to_dict()


@router.post("/procedural-animation/create-motion")
async def create_procedural_motion(request: Request):
    """Create a procedural motion."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    body = await request.json()
    pa = get_procedural_animation()
    motion = pa.create_procedural_motion(
        skeleton_id=body.get("skeleton_id", ""),
        motion_style=body.get("motion_style", "walk"),
        speed=body.get("speed", 1.0),
        stride_length=body.get("stride_length", 1.0),
        step_height=body.get("step_height", 0.3),
    )
    return motion.to_dict()


@router.post("/procedural-animation/update-motion")
async def update_procedural_motion(request: Request):
    """Update procedural animation frame."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    body = await request.json()
    pa = get_procedural_animation()
    skeleton = pa.update_procedural_motion(
        motion_id=body.get("motion_id", ""),
        delta_time=body.get("delta_time", 0.016),
        ground_contacts=body.get("ground_contacts"),
    )
    return skeleton.to_dict()


@router.post("/procedural-animation/create-blend")
async def create_animation_blend(request: Request):
    """Create an animation blend tree."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    body = await request.json()
    pa = get_procedural_animation()
    animations = body.get("animations", "")
    if isinstance(animations, str):
        animations = [a.strip() for a in animations.split(",") if a.strip()]
    blend = pa.create_blend_tree(
        skeleton_id=body.get("skeleton_id", ""),
        animations=animations,
        blend_mode=body.get("blend_mode", "linear"),
        blend_duration=body.get("blend_duration", 0.3),
    )
    return blend.to_dict()


@router.post("/procedural-animation/update-blend")
async def update_animation_blend(request: Request):
    """Evaluate blend tree with weights."""
    from sparkai.engine.engine_procedural_animation import get_procedural_animation
    body = await request.json()
    pa = get_procedural_animation()
    skeleton = pa.update_blend_tree(
        blend_id=body.get("blend_id", ""),
        weights=body.get("weights", []),
        delta_time=body.get("delta_time", 0.016),
    )
    return skeleton.to_dict()

# ---------------------------------------------------------------------------
# Object Pool Routes
# ---------------------------------------------------------------------------

@router.get("/object-pool/status")
async def object_pool_status():
    """Get object pool system status."""
    from sparkai.engine.engine_object_pool import get_object_pool
    op = get_object_pool()
    return op.get_status()


@router.post("/object-pool/create-pool")
async def create_object_pool(request: Request):
    """Create a new object pool."""
    from sparkai.engine.engine_object_pool import get_object_pool
    body = await request.json()
    op = get_object_pool()
    config = op.create_pool(
        name=body.get("pool_name", ""),
        object_type=body.get("object_type", ""),
        config_params={
            "strategy": body.get("strategy", "dynamic_growth"),
            "initial_size": body.get("initial_size", 10),
            "max_size": body.get("max_size", 100),
            "growth_factor": body.get("growth_factor", 1.5),
            "allocation_policy": body.get("allocation_policy", "round_robin"),
        },
    )
    return config.to_dict()


@router.post("/object-pool/borrow")
async def borrow_object(request: Request):
    """Borrow an object from pool."""
    from sparkai.engine.engine_object_pool import get_object_pool
    body = await request.json()
    op = get_object_pool()
    obj = op.borrow_object(
        pool_id=body.get("pool_id", ""),
        required_properties=body.get("required_properties", {}),
    )
    return obj.to_dict() if obj else {"error": "No available object"}


@router.post("/object-pool/return")
async def return_object(request: Request):
    """Return an object to pool."""
    from sparkai.engine.engine_object_pool import get_object_pool
    body = await request.json()
    op = get_object_pool()
    success = op.return_object(
        pool_id=body.get("pool_id", ""),
        object_id=body.get("object_id", ""),
    )
    return {"success": success}


@router.post("/object-pool/prewarm")
async def prewarm_pool(request: Request):
    """Pre-allocate objects in pool."""
    from sparkai.engine.engine_object_pool import get_object_pool
    body = await request.json()
    op = get_object_pool()
    count = op.prewarm_pool(
        pool_id=body.get("pool_id", ""),
        count=body.get("count", 5),
        background=body.get("background", False),
    )
    return {"prewarmed": count}


@router.post("/object-pool/recycle")
async def recycle_pool(request: Request):
    """Force recycle inactive objects."""
    from sparkai.engine.engine_object_pool import get_object_pool
    body = await request.json()
    op = get_object_pool()
    count = op.recycle_pool(pool_id=body.get("pool_id", ""))
    return {"recycled": count}


@router.post("/object-pool/force-gc")
async def force_gc_pool(request: Request):
    """Force garbage collect excess objects."""
    from sparkai.engine.engine_object_pool import get_object_pool
    body = await request.json()
    op = get_object_pool()
    count = op.force_gc(pool_id=body.get("pool_id", ""))
    return {"collected": count}


@router.post("/object-pool/predict-demand")
async def predict_object_demand(request: Request):
    """Predict future object demand."""
    from sparkai.engine.engine_object_pool import get_object_pool
    body = await request.json()
    op = get_object_pool()
    demand = op.predict_demand(
        pool_id=body.get("pool_id", ""),
        time_window_seconds=body.get("time_window_seconds", 60),
    )
    return {"predicted_demand": demand}


@router.post("/object-pool/auto-optimize")
async def auto_optimize_pools():
    """Run automatic optimization across all pools."""
    from sparkai.engine.engine_object_pool import get_object_pool
    op = get_object_pool()
    result = op.auto_optimize()
    return result

# ---------------------------------------------------------------------------
# Runtime Scripting Routes
# ---------------------------------------------------------------------------

@router.get("/runtime-scripting/status")
async def runtime_scripting_status():
    """Get runtime scripting system status."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    rs = get_runtime_scripting()
    return rs.get_status()


@router.post("/runtime-scripting/register")
async def register_script(request: Request):
    """Register a new script."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    events = body.get("events", [])
    if isinstance(events, str):
        events = [e.strip() for e in events.split(",") if e.strip()]
    script = rs.register_script(
        name=body.get("name", ""),
        language=body.get("language", "python"),
        scope=body.get("scope", "entity"),
        source_code=body.get("source_code", ""),
        events=events,
        dependencies=body.get("dependencies", []),
    )
    return script.to_dict()


@router.post("/runtime-scripting/compile")
async def compile_script(request: Request):
    """Compile/validate script syntax."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    script = rs.compile_script(script_id=body.get("script_id", ""))
    return script.to_dict() if script else {"error": "Script not found"}


@router.post("/runtime-scripting/instantiate")
async def instantiate_script(request: Request):
    """Create a script instance."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    instance = rs.instantiate_script(
        script_id=body.get("script_id", ""),
        target_entity_id=body.get("target_entity_id"),
        initial_variables=body.get("initial_variables", {}),
    )
    return instance.to_dict() if instance else {"error": "Script not found"}


@router.post("/runtime-scripting/execute")
async def execute_script(request: Request):
    """Execute a script instance."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting, ScriptEventType
    body = await request.json()
    rs = get_runtime_scripting()
    context = {"delta_time": body.get("delta_time", 0.016), "frame_number": 0}
    result = rs.execute_script(
        instance_id=body.get("instance_id", ""),
        context=context,
    )
    return result


@router.post("/runtime-scripting/hot-reload")
async def hot_reload_script(request: Request):
    """Hot-reload script at runtime."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    script = rs.hot_reload(
        script_id=body.get("script_id", ""),
        new_source=body.get("new_source", ""),
    )
    return script.to_dict() if script else {"error": "Script not found"}


@router.post("/runtime-scripting/trigger-event")
async def trigger_script_event(request: Request):
    """Trigger event on script."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    results = rs.trigger_event(
        script_id=body.get("script_id", ""),
        event_type=body.get("event_type", "on_start"),
        event_data=body.get("event_data", {}),
    )
    return {"results": results, "count": len(results)}


@router.post("/runtime-scripting/pause")
async def pause_script(request: Request):
    """Pause script execution."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    success = rs.pause_instance(instance_id=body.get("instance_id", ""))
    return {"success": success}


@router.post("/runtime-scripting/resume")
async def resume_script(request: Request):
    """Resume script execution."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    success = rs.resume_instance(instance_id=body.get("instance_id", ""))
    return {"success": success}


@router.post("/runtime-scripting/set-variable")
async def set_script_variable(request: Request):
    """Set a script variable."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    success = rs.set_variable(
        instance_id=body.get("instance_id", ""),
        name=body.get("name", ""),
        value=body.get("value"),
    )
    return {"success": success}


@router.post("/runtime-scripting/register-handler")
async def register_event_handler(request: Request):
    """Register an event handler."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    success = rs.register_event_handler(
        script_id=body.get("script_id", ""),
        event_type=body.get("event_type", "on_start"),
        handler_code=body.get("handler_code", ""),
    )
    return {"success": success}


@router.post("/runtime-scripting/schedule")
async def schedule_script(request: Request):
    """Schedule future script execution."""
    from sparkai.engine.engine_runtime_scripting import get_runtime_scripting
    body = await request.json()
    rs = get_runtime_scripting()
    schedule_id = rs.schedule_execution(
        script_id=body.get("script_id", ""),
        delay_ms=body.get("delay_ms", 1000),
        repeat=body.get("repeat", False),
        context=body.get("context", {}),
    )
    return {"schedule_id": schedule_id}


# ---------------------------------------------------------------------------
# Sprite Batcher Routes
# ---------------------------------------------------------------------------


@router.get("/sprite-batcher/status")
async def sprite_batcher_status():
    """Get sprite batcher statistics."""
    from sparkai.engine.engine_sprite_batcher import get_sprite_batcher
    sb = get_sprite_batcher()
    return sb.get_render_stats()

@router.get("/sprite-batcher/stats")
async def sprite_batcher_stats():
    """Get sprite batcher statistics (alias for status)."""
    try:
        from sparkai.engine.engine_sprite_batcher import get_sprite_batcher
        sb = get_sprite_batcher()
        return sb.get_render_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/sprite-batcher/submit")
async def sprite_batcher_submit(request: Request):
    """Submit a sprite draw command to the batcher."""
    from sparkai.engine.engine_sprite_batcher import get_sprite_batcher, BlendMode
    body = await request.json()
    sb = get_sprite_batcher()

    try:
        blend = BlendMode(body.get("blend_mode", "normal"))
    except ValueError:
        blend = BlendMode.NORMAL

    command = sb.submit_sprite(
        texture_name=body.get("texture_name", ""),
        position_x=body.get("position_x", 0.0),
        position_y=body.get("position_y", 0.0),
        scale_x=body.get("scale_x", 1.0),
        scale_y=body.get("scale_y", 1.0),
        rotation_degrees=body.get("rotation_degrees", 0.0),
        color_rgba=tuple(body.get("color_rgba", [255, 255, 255, 255])),
        blend_mode=blend,
        z_order=body.get("z_order", 0),
    )
    return command.to_dict()


@router.post("/sprite-batcher/flush")
async def sprite_batcher_flush():
    """Flush command buffer into optimized GPU batches."""
    from sparkai.engine.engine_sprite_batcher import get_sprite_batcher
    sb = get_sprite_batcher()
    batches = sb.flush_batches()
    return {"batches": [b.to_dict() for b in batches], "count": len(batches)}


@router.post("/sprite-batcher/clear")
async def sprite_batcher_clear():
    """Clear the command buffer for the next frame."""
    from sparkai.engine.engine_sprite_batcher import get_sprite_batcher
    sb = get_sprite_batcher()
    sb.clear_frame()
    return {"cleared": True}


@router.post("/sprite-batcher/create-atlas")
async def sprite_batcher_create_atlas(request: Request):
    """Create a texture atlas from multiple textures."""
    from sparkai.engine.engine_sprite_batcher import get_sprite_batcher, AtlasPackMode
    body = await request.json()
    sb = get_sprite_batcher()

    try:
        pack = AtlasPackMode(body.get("pack_mode", "bin_pack"))
    except ValueError:
        pack = AtlasPackMode.BIN_PACK

    atlas = sb.create_texture_atlas(
        name=body.get("name", ""),
        texture_names=body.get("texture_names", []),
        size=body.get("size", 2048),
        pack_mode=pack,
    )
    return atlas.to_dict()


@router.get("/sprite-batcher/atlases")
async def sprite_batcher_atlases():
    """List all texture atlases."""
    from sparkai.engine.engine_sprite_batcher import get_sprite_batcher
    sb = get_sprite_batcher()
    return {"atlases": sb.list_atlases()}


@router.get("/sprite-batcher/frame-report")
async def sprite_batcher_frame_report():
    """Get current frame batch report."""
    from sparkai.engine.engine_sprite_batcher import get_sprite_batcher
    sb = get_sprite_batcher()
    return sb.get_frame_report()


# ---------------------------------------------------------------------------
# Visual Event Sheet Routes
# ---------------------------------------------------------------------------


@router.get("/visual-event-sheet/status")
async def visual_event_sheet_status():
    """Get visual event sheet system statistics."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
    ves = get_visual_event_sheet()
    return ves.get_statistics()

@router.get("/visual-event-sheet/stats")
async def visual_event_sheet_stats():
    """Get visual event sheet statistics (alias for status)."""
    try:
        from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
        ves = get_visual_event_sheet()
        return ves.get_statistics()
    except Exception as e:
        return {"error": str(e)}


@router.post("/visual-event-sheet/create")
async def visual_event_sheet_create(request: Request):
    """Create a new event sheet."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet, EventScope
    body = await request.json()
    ves = get_visual_event_sheet()

    try:
        scope = EventScope(body.get("scope", "scene"))
    except ValueError:
        scope = EventScope.SCENE

    sheet = ves.create_sheet(
        name=body.get("name", ""),
        scope=scope,
        description=body.get("description", ""),
    )
    return sheet.to_dict()


@router.get("/visual-event-sheet/list")
async def visual_event_sheet_list():
    """List event sheets."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
    ves = get_visual_event_sheet()
    return {"sheets": ves.list_sheets()}


@router.post("/visual-event-sheet/add-event")
async def visual_event_sheet_add_event(request: Request):
    """Add a condition-action event to a sheet."""
    from sparkai.engine.engine_visual_event_sheet import (
        get_visual_event_sheet, EventTrigger, EventCondition,
        EventAction, ConditionOperator, ActionType
    )
    body = await request.json()
    ves = get_visual_event_sheet()

    try:
        trigger = EventTrigger(body.get("trigger", "every_frame"))
    except ValueError:
        trigger = EventTrigger.EVERY_FRAME

    conditions = []
    for c in body.get("conditions", []):
        try:
            op = ConditionOperator(c.get("operator", "equal"))
        except ValueError:
            op = ConditionOperator.EQUAL
        conditions.append(EventCondition(
            operator=op,
            left_operand=c.get("left_operand", ""),
            right_operand=c.get("right_operand"),
            invert=c.get("invert", False),
            description=c.get("description", ""),
        ))

    actions = []
    for a in body.get("actions", []):
        try:
            at = ActionType(a.get("action_type", "object"))
        except ValueError:
            at = ActionType.OBJECT
        actions.append(EventAction(
            action_type=at,
            action_name=a.get("action_name", ""),
            parameters=a.get("parameters", {}),
            target_object=a.get("target_object", ""),
            delay_ms=a.get("delay_ms", 0.0),
        ))

    event = ves.add_event(
        sheet_id=body.get("sheet_id", ""),
        name=body.get("name", ""),
        trigger=trigger,
        conditions=conditions,
        actions=actions,
        priority=body.get("priority", 0),
    )
    return event.to_dict() if event else {"error": "Sheet not found"}


@router.post("/visual-event-sheet/add-sub-event")
async def visual_event_sheet_add_sub_event(request: Request):
    """Add a nested sub-event to a parent event."""
    from sparkai.engine.engine_visual_event_sheet import (
        get_visual_event_sheet, EventCondition, EventAction,
        ConditionOperator, ActionType
    )
    body = await request.json()
    ves = get_visual_event_sheet()

    conditions = []
    for c in body.get("conditions", []):
        try:
            op = ConditionOperator(c.get("operator", "equal"))
        except ValueError:
            op = ConditionOperator.EQUAL
        conditions.append(EventCondition(
            operator=op,
            left_operand=c.get("left_operand", ""),
            right_operand=c.get("right_operand"),
        ))

    actions = []
    for a in body.get("actions", []):
        try:
            at = ActionType(a.get("action_type", "object"))
        except ValueError:
            at = ActionType.OBJECT
        actions.append(EventAction(
            action_type=at,
            action_name=a.get("action_name", ""),
            parameters=a.get("parameters", {}),
        ))

    sub = ves.add_sub_event(
        sheet_id=body.get("sheet_id", ""),
        event_id=body.get("event_id", ""),
        conditions=conditions,
        actions=actions,
    )
    return sub.to_dict() if sub else {"error": "Parent event not found"}


@router.post("/visual-event-sheet/evaluate")
async def visual_event_sheet_evaluate(request: Request):
    """Evaluate an event sheet against current runtime state."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
    body = await request.json()
    ves = get_visual_event_sheet()
    result = ves.evaluate_sheet(
        sheet_id=body.get("sheet_id", ""),
        custom_state=body.get("custom_state"),
    )
    return result


@router.post("/visual-event-sheet/clone")
async def visual_event_sheet_clone(request: Request):
    """Deep-copy an event sheet."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
    body = await request.json()
    ves = get_visual_event_sheet()
    cloned = ves.clone_sheet(
        sheet_id=body.get("sheet_id", ""),
        new_name=body.get("new_name", "Cloned Sheet"),
    )
    return cloned.to_dict() if cloned else {"error": "Source sheet not found"}


@router.post("/visual-event-sheet/validate")
async def visual_event_sheet_validate(request: Request):
    """Validate an event sheet for errors."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
    body = await request.json()
    ves = get_visual_event_sheet()
    result = ves.validate_sheet(sheet_id=body.get("sheet_id", ""))
    return result


@router.post("/visual-event-sheet/compile")
async def visual_event_sheet_compile(request: Request):
    """Pre-compile an event sheet for runtime."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
    body = await request.json()
    ves = get_visual_event_sheet()
    result = ves.compile_sheet(sheet_id=body.get("sheet_id", ""))
    return result


@router.get("/visual-event-sheet/execution-log")
async def visual_event_sheet_execution_log():
    """Get recent execution log."""
    from sparkai.engine.engine_visual_event_sheet import get_visual_event_sheet
    ves = get_visual_event_sheet()
    return {"log": ves.get_execution_log(limit=20)}


# ---------------------------------------------------------------------------
# Node Composer Routes
# ---------------------------------------------------------------------------


@router.get("/node-composer/status")
async def node_composer_status():
    """Get node composer statistics."""
    from sparkai.engine.engine_node_composer import get_node_composer
    nc = get_node_composer()
    return nc.get_statistics()

@router.get("/node-composer/stats")
async def node_composer_stats():
    """Get node composer statistics (alias for status)."""
    try:
        from sparkai.engine.engine_node_composer import get_node_composer
        nc = get_node_composer()
        return nc.get_statistics()
    except Exception as e:
        return {"error": str(e)}


@router.post("/node-composer/build-tree")
async def node_composer_build_tree(request: Request):
    """Create a new node tree with a root node."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()
    tree = nc.build_tree(
        name=body.get("name", ""),
        root_name=body.get("root_name", "Root"),
        metadata=body.get("metadata"),
    )
    return tree.to_dict()


@router.get("/node-composer/trees")
async def node_composer_trees():
    """List all node trees."""
    from sparkai.engine.engine_node_composer import get_node_composer
    nc = get_node_composer()
    return {"trees": nc.list_trees()}


@router.post("/node-composer/create-node")
async def node_composer_create_node(request: Request):
    """Create a new scene node."""
    from sparkai.engine.engine_node_composer import get_node_composer, NodeType
    body = await request.json()
    nc = get_node_composer()

    try:
        ntype = NodeType(body.get("node_type", "group"))
    except ValueError:
        ntype = NodeType.GROUP

    node = nc.create_node(
        name=body.get("name", ""),
        node_type=ntype,
        position_x=body.get("position_x", 0.0),
        position_y=body.get("position_y", 0.0),
        rotation_degrees=body.get("rotation_degrees", 0.0),
        scale_x=body.get("scale_x", 1.0),
        scale_y=body.get("scale_y", 1.0),
        properties=body.get("properties"),
        tags=body.get("tags"),
    )
    return node.to_dict()


@router.post("/node-composer/add-child")
async def node_composer_add_child(request: Request):
    """Attach a child node to a parent with transform inheritance."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()

    # Create the child node from request data
    child = nc.create_node(
        name=body.get("child_name", "Child"),
        position_x=body.get("position_x", 0.0),
        position_y=body.get("position_y", 0.0),
    )

    success = nc.add_child(
        tree_id=body.get("tree_id", ""),
        parent_id=body.get("parent_id", ""),
        child=child,
    )
    return {"success": success, "child_id": child.node_id if success else ""}


@router.post("/node-composer/reparent")
async def node_composer_reparent(request: Request):
    """Move a node to a different parent."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()
    success = nc.reparent(
        tree_id=body.get("tree_id", ""),
        node_id=body.get("node_id", ""),
        new_parent_id=body.get("new_parent_id", ""),
    )
    return {"success": success}


@router.post("/node-composer/query")
async def node_composer_query(request: Request):
    """Query nodes by type, name, tags, or state."""
    from sparkai.engine.engine_node_composer import get_node_composer, NodeType, NodeState
    body = await request.json()
    nc = get_node_composer()

    node_type = body.get("node_type")
    if node_type:
        try:
            node_type = NodeType(node_type)
        except ValueError:
            node_type = None

    state = body.get("state")
    if state:
        try:
            state = NodeState(state)
        except ValueError:
            state = None

    nodes = nc.query_nodes(
        tree_id=body.get("tree_id", ""),
        node_type=node_type,
        name_pattern=body.get("name_pattern"),
        tags=body.get("tags"),
        state=state,
    )
    return {"nodes": [n.to_dict() for n in nodes], "count": len(nodes)}


@router.post("/node-composer/get-by-path")
async def node_composer_get_by_path(request: Request):
    """Find a node by hierarchical path."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()
    node = nc.get_node_by_path(
        tree_id=body.get("tree_id", ""),
        path=body.get("path", "/"),
    )
    return node.to_dict() if node else {"error": "Node not found"}


@router.post("/node-composer/send-signal")
async def node_composer_send_signal(request: Request):
    """Emit a signal through the node tree."""
    from sparkai.engine.engine_node_composer import get_node_composer, SignalDirection
    body = await request.json()
    nc = get_node_composer()

    try:
        direction = SignalDirection(body.get("direction", "downward"))
    except ValueError:
        direction = SignalDirection.DOWNWARD

    recipients = nc.send_signal(
        tree_id=body.get("tree_id", ""),
        signal_name=body.get("signal_name", ""),
        source_node_id=body.get("source_node_id", ""),
        data=body.get("data"),
        direction=direction,
        target_node_id=body.get("target_node_id"),
    )
    return {"recipients": recipients, "count": len(recipients)}


@router.post("/node-composer/freeze-branch")
async def node_composer_freeze_branch(request: Request):
    """Freeze (pause) a node branch."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()
    count = nc.freeze_branch(
        tree_id=body.get("tree_id", ""),
        node_id=body.get("node_id", ""),
    )
    return {"frozen_count": count}


@router.post("/node-composer/thaw-branch")
async def node_composer_thaw_branch(request: Request):
    """Thaw (resume) a frozen node branch."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()
    count = nc.thaw_branch(
        tree_id=body.get("tree_id", ""),
        node_id=body.get("node_id", ""),
    )
    return {"thawed_count": count}


@router.post("/node-composer/export-tree")
async def node_composer_export_tree(request: Request):
    """Export a complete node tree to portable format."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()
    exported = nc.export_tree(tree_id=body.get("tree_id", ""))
    return exported if exported else {"error": "Tree not found"}


@router.post("/node-composer/create-group")
async def node_composer_create_group(request: Request):
    """Create a logical node group."""
    from sparkai.engine.engine_node_composer import get_node_composer
    body = await request.json()
    nc = get_node_composer()
    group = nc.create_group(
        tree_id=body.get("tree_id", ""),
        name=body.get("name", ""),
        node_ids=body.get("node_ids"),
    )
    return group.to_dict() if group else {"error": "Tree not found"}
# ---------------------------------------------------------------------------
# Particle System Routes
# ---------------------------------------------------------------------------

@router.post("/particle-system/create-emitter")
async def particle_system_create_emitter(request: Request):
    """Create a particle emitter."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system, EmitterConfig
        body = await request.json()
        ps = get_particle_system()
        config = EmitterConfig(
            name=body.get("name", "emitter"),
            texture_id=body.get("texture_id", ""),
            emission_shape=body.get("emission_shape", "point"),
            emission_rate=body.get("emission_rate", 100.0),
            life_min=body.get("life_min", 0.5),
            life_max=body.get("life_max", 1.0),
            speed_min=body.get("speed_min", 100.0),
            speed_max=body.get("speed_max", 200.0),
            angle_min=body.get("angle_min", 0.0),
            angle_max=body.get("angle_max", 360.0),
            size_start_min=body.get("size_start_min", 1.0),
            size_start_max=body.get("size_start_max", 1.0),
            size_end_min=body.get("size_end_min", 0.5),
            size_end_max=body.get("size_end_max", 0.5),
            color_start=body.get("color_start", (255, 255, 255, 255)),
            color_end=body.get("color_end", (255, 255, 255, 0)),
            gravity_x=body.get("gravity_x", 0.0),
            gravity_y=body.get("gravity_y", 0.0),
            radial_accel=body.get("radial_accel", 0.0),
            tangential_accel=body.get("tangential_accel", 0.0),
            damping=body.get("damping", 0.0),
            blend_mode=body.get("blend_mode", "normal"),
            max_particles=body.get("max_particles", 500),
            emitter_lifetime=body.get("emitter_lifetime", -1),
            emitter_duration=body.get("emitter_duration", 0.0),
            emission_burst_count=body.get("emission_burst_count", 0),
            simulation_space=body.get("simulation_space", "world"),
            circle_radius=body.get("circle_radius", 0.0),
            rect_width=body.get("rect_width", 0.0),
            rect_height=body.get("rect_height", 0.0),
            ring_inner_radius=body.get("ring_inner_radius", 0.0),
            ring_outer_radius=body.get("ring_outer_radius", 0.0),
            cone_angle=body.get("cone_angle", 0.0),
            line_length=body.get("line_length", 0.0),
        )
        emitter = ps.create_emitter(
            config=config,
            pos_x=body.get("pos_x", 0.0),
            pos_y=body.get("pos_y", 0.0),
            rotation=body.get("rotation", 0.0),
        )
        return emitter.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/particle-system/update-all")
async def particle_system_update_all(request: Request):
    """Update all particle emitters."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        body = await request.json()
        ps = get_particle_system()
        result = ps.update_all(delta_time=body.get("delta_time", 0.016))
        return {k: [p.to_dict() for p in v] for k, v in result.items()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/particle-system/update-emitter")
async def particle_system_update_emitter(request: Request):
    """Update a single particle emitter."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        body = await request.json()
        ps = get_particle_system()
        particles = ps.update_emitter(
            emitter_id=body.get("emitter_id", ""),
            delta_time=body.get("delta_time", 0.016),
        )
        return [p.to_dict() for p in particles]
    except Exception as e:
        return {"error": str(e)}


@router.get("/particle-system/emitter-state")
async def particle_system_emitter_state(request: Request):
    """Get emitter state."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        ps = get_particle_system()
        state = ps.get_emitter_state(emitter_id=request.query_params.get("emitter_id", ""))
        return state.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/particle-system/set-emitter-position")
async def particle_system_set_emitter_position(request: Request):
    """Set emitter position."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        body = await request.json()
        ps = get_particle_system()
        ps.set_emitter_position(
            emitter_id=body.get("emitter_id", ""),
            x=body.get("x", 0.0),
            y=body.get("y", 0.0),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/particle-system/set-emitter-active")
async def particle_system_set_emitter_active(request: Request):
    """Set emitter active state."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        body = await request.json()
        ps = get_particle_system()
        ps.set_emitter_active(
            emitter_id=body.get("emitter_id", ""),
            active=body.get("active", True),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/particle-system/remove-emitter")
async def particle_system_remove_emitter(request: Request):
    """Remove an emitter."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        body = await request.json()
        ps = get_particle_system()
        ps.remove_emitter(emitter_id=body.get("emitter_id", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/particle-system/burst")
async def particle_system_burst(request: Request):
    """Burst particles from an emitter."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        body = await request.json()
        ps = get_particle_system()
        particles = ps.burst(
            emitter_id=body.get("emitter_id", ""),
            count=body.get("count", 50),
        )
        return [p.to_dict() for p in particles]
    except Exception as e:
        return {"error": str(e)}


@router.get("/particle-system/stats")
async def particle_system_stats():
    """Get particle system statistics."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        ps = get_particle_system()
        return ps.get_active_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/particle-system/clear")
async def particle_system_clear():
    """Clear all emitters."""
    try:
        from sparkai.engine.engine_particle_system import get_particle_system
        ps = get_particle_system()
        ps.clear_all()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tilemap System Routes
# ---------------------------------------------------------------------------

@router.post("/tilemap-system/create-tilemap")
async def tilemap_system_create_tilemap(request: Request):
    """Create a tilemap."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        result = tm.create_tilemap(
            name=body.get("name", ""),
            width=body.get("width", 0),
            height=body.get("height", 0),
            tile_width=body.get("tile_width", 0),
            tile_height=body.get("tile_height", 0),
            orientation=body.get("orientation", "orthogonal"),
        )
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/create-tileset")
async def tilemap_system_create_tileset(request: Request):
    """Create a tileset."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        tileset = tm.create_tileset(
            name=body.get("name", ""),
            tile_width=body.get("tile_width", 0),
            tile_height=body.get("tile_height", 0),
            image_width=body.get("image_width", 0),
            image_height=body.get("image_height", 0),
            margin=body.get("margin", 0),
            spacing=body.get("spacing", 0),
        )
        return tileset.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/set-tile")
async def tilemap_system_set_tile(request: Request):
    """Set a tile in the tilemap."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        result = tm.set_tile(
            tilemap_id=body.get("tilemap_id", ""),
            layer_id=body.get("layer_id", ""),
            x=body.get("x", 0),
            y=body.get("y", 0),
            global_tile_id=body.get("global_tile_id", 0),
            tileset_id=body.get("tileset_id", ""),
            flags=body.get("flags"),
        )
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/fill-rect")
async def tilemap_system_fill_rect(request: Request):
    """Fill a rectangular region with tiles."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        tm.fill_rect(
            tilemap_id=body.get("tilemap_id", ""),
            layer_id=body.get("layer_id", ""),
            x=body.get("x", 0),
            y=body.get("y", 0),
            w=body.get("w", 1),
            h=body.get("h", 1),
            global_tile_id=body.get("global_tile_id", 0),
            tileset_id=body.get("tileset_id", ""),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/add-layer")
async def tilemap_system_add_layer(request: Request):
    """Add a tile layer."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        layer = tm.add_layer(
            tilemap_id=body.get("tilemap_id", ""),
            name=body.get("name", ""),
            z_order=body.get("z_order", 0),
        )
        return layer.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/add-object-layer")
async def tilemap_system_add_object_layer(request: Request):
    """Add an object layer."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        layer = tm.add_object_layer(
            tilemap_id=body.get("tilemap_id", ""),
            name=body.get("name", ""),
            z_order=body.get("z_order", 0),
        )
        return layer.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/add-object")
async def tilemap_system_add_object(request: Request):
    """Add an object to an object layer."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        obj = tm.add_tilemap_object(
            tilemap_id=body.get("tilemap_id", ""),
            object_layer_id=body.get("object_layer_id", ""),
            name=body.get("name", ""),
            obj_type=body.get("obj_type", ""),
            x=body.get("x", 0.0),
            y=body.get("y", 0.0),
            width=body.get("width", 0.0),
            height=body.get("height", 0.0),
        )
        return obj.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/world-to-tile")
async def tilemap_system_world_to_tile(request: Request):
    """Convert world coordinates to tile coordinates."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        tx, ty = tm.world_to_tile(
            tilemap_id=body.get("tilemap_id", ""),
            world_x=body.get("world_x", 0.0),
            world_y=body.get("world_y", 0.0),
        )
        return {"tile_x": tx, "tile_y": ty}
    except Exception as e:
        return {"error": str(e)}


@router.post("/tilemap-system/tile-to-world")
async def tilemap_system_tile_to_world(request: Request):
    """Convert tile coordinates to world coordinates."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        body = await request.json()
        tm = get_tilemap_system()
        wx, wy = tm.tile_to_world(
            tilemap_id=body.get("tilemap_id", ""),
            tile_x=body.get("tile_x", 0),
            tile_y=body.get("tile_y", 0),
        )
        return {"world_x": wx, "world_y": wy}
    except Exception as e:
        return {"error": str(e)}


@router.get("/tilemap-system/collision-tiles")
async def tilemap_system_collision_tiles(request: Request):
    """Get collision tiles."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        tm = get_tilemap_system()
        return tm.get_collision_tiles(
            tilemap_id=request.query_params.get("tilemap_id", ""),
            layer_id=request.query_params.get("layer_id", ""),
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/tilemap-system/stats")
async def tilemap_system_stats(request: Request):
    """Get tilemap statistics."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        tm = get_tilemap_system()
        return tm.get_tilemap_stats(
            tilemap_id=request.query_params.get("tilemap_id", ""),
        )
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Input Mapping Routes
# ---------------------------------------------------------------------------

@router.post("/input-mapping/create-map")
async def input_mapping_create_map(request: Request):
    """Create an action map."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        body = await request.json()
        im = get_input_mapping()
        map_obj = im.create_action_map(
            name=body.get("name", "default"),
            priority=body.get("priority", 0),
        )
        return map_obj.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/register-action")
async def input_mapping_register_action(request: Request):
    """Register an input action."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping, ActionDefinition
        body = await request.json()
        im = get_input_mapping()
        action = ActionDefinition(
            name=body.get("name", ""),
            display_name=body.get("display_name", ""),
            action_type=body.get("action_type", "digital"),
            analog_dead_zone=body.get("analog_dead_zone", 0.15),
            analog_sensitivity=body.get("analog_sensitivity", 1.0),
            is_toggle=body.get("is_toggle", False),
        )
        result = im.register_action(
            map_id=body.get("map_id", ""),
            action=action,
        )
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/bind-input")
async def input_mapping_bind_input(request: Request):
    """Bind an input to an action."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping, InputBinding
        body = await request.json()
        im = get_input_mapping()
        binding = InputBinding(
            action_name=body.get("action_name", ""),
            device=body.get("device", "keyboard"),
            input_code=body.get("input_code", ""),
            event_type=body.get("event_type", "pressed"),
            scale=body.get("scale", 1.0),
            chord_modifier=body.get("chord_modifier"),
            chord_key=body.get("chord_key"),
            zone=body.get("zone"),
        )
        result = im.bind_input(
            map_id=body.get("map_id", ""),
            action_name=body.get("action_name", ""),
            binding=binding,
        )
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/register-chord")
async def input_mapping_register_chord(request: Request):
    """Register a chord definition."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping, ChordDefinition
        body = await request.json()
        im = get_input_mapping()
        chord = ChordDefinition(
            name=body.get("name", ""),
            keys=body.get("keys", []),
            action_name=body.get("action_name", ""),
        )
        result = im.register_chord(chord)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/key-event")
async def input_mapping_key_event(request: Request):
    """Process a key event."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        body = await request.json()
        im = get_input_mapping()
        states = im.process_key_event(
            key_code=body.get("key_code", ""),
            pressed=body.get("pressed", True),
        )
        return {k: v.to_dict() for k, v in states.items()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/mouse-event")
async def input_mapping_mouse_event(request: Request):
    """Process a mouse event."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        body = await request.json()
        im = get_input_mapping()
        states = im.process_mouse_event(
            button_code=body.get("button_code", ""),
            pressed=body.get("pressed", True),
            x=body.get("x", 0.0),
            y=body.get("y", 0.0),
        )
        return {k: v.to_dict() for k, v in states.items()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/mouse-move")
async def input_mapping_mouse_move(request: Request):
    """Process mouse movement."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        body = await request.json()
        im = get_input_mapping()
        im.process_mouse_move(
            x=body.get("x", 0.0),
            y=body.get("y", 0.0),
            delta_x=body.get("delta_x", 0.0),
            delta_y=body.get("delta_y", 0.0),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/gamepad-button")
async def input_mapping_gamepad_button(request: Request):
    """Process a gamepad button event."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        body = await request.json()
        im = get_input_mapping()
        states = im.process_gamepad_button(
            gamepad_id=body.get("gamepad_id", 0),
            button_code=body.get("button_code", ""),
            pressed=body.get("pressed", True),
        )
        return {k: v.to_dict() for k, v in states.items()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/gamepad-axis")
async def input_mapping_gamepad_axis(request: Request):
    """Process a gamepad axis event."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        body = await request.json()
        im = get_input_mapping()
        states = im.process_gamepad_axis(
            gamepad_id=body.get("gamepad_id", 0),
            axis_code=body.get("axis_code", ""),
            value=body.get("value", 0.0),
        )
        return {k: v.to_dict() for k, v in states.items()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/build-frame")
async def input_mapping_build_frame(request: Request):
    """Build the input frame."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        im = get_input_mapping()
        frame = im.build_frame()
        return frame.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/input-mapping/action-state")
async def input_mapping_action_state(request: Request):
    """Get action state."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        im = get_input_mapping()
        state = im.get_action_state(action_name=request.query_params.get("action_name", ""))
        return state.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/input-mapping/set-map-enabled")
async def input_mapping_set_map_enabled(request: Request):
    """Enable or disable an action map."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        body = await request.json()
        im = get_input_mapping()
        im.set_action_map_enabled(
            map_id=body.get("map_id", ""),
            enabled=body.get("enabled", True),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.get("/input-mapping/stats")
async def input_mapping_stats():
    """Get input mapping statistics."""
    try:
        from sparkai.engine.engine_input_mapping import get_input_mapping
        im = get_input_mapping()
        return im.get_input_stats()
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Camera System Routes
# ---------------------------------------------------------------------------

@router.post("/camera-system/create")
async def camera_system_create(request: Request):
    """Create a camera."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        camera = cs.create_camera(
            name=body.get("name", "main"),
            viewport_w=body.get("viewport_w", 1920),
            viewport_h=body.get("viewport_h", 1080),
        )
        return camera.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/set-position")
async def camera_system_set_position(request: Request):
    """Set camera position."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        cs.set_camera_position(
            camera_id=body.get("camera_id", ""),
            x=body.get("x", 0.0),
            y=body.get("y", 0.0),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/set-zoom")
async def camera_system_set_zoom(request: Request):
    """Set camera zoom."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        cs.set_camera_zoom(
            camera_id=body.get("camera_id", ""),
            zoom=body.get("zoom", 1.0),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/set-rotation")
async def camera_system_set_rotation(request: Request):
    """Set camera rotation."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        cs.set_camera_rotation(
            camera_id=body.get("camera_id", ""),
            degrees=body.get("degrees", 0.0),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/set-follow")
async def camera_system_set_follow(request: Request):
    """Set camera follow target."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system, CameraTarget
        body = await request.json()
        cs = get_camera_system()
        target = CameraTarget(
            target_id=body.get("target_id", ""),
            offset_x=body.get("offset_x", 0.0),
            offset_y=body.get("offset_y", 0.0),
            smooth_speed=body.get("smooth_speed", 5.0),
            dead_zone_x=body.get("dead_zone_x", 0.0),
            dead_zone_y=body.get("dead_zone_y", 0.0),
            look_ahead=body.get("look_ahead", 0.0),
        )
        cs.set_follow_target(
            camera_id=body.get("camera_id", ""),
            target=target,
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/update-follow")
async def camera_system_update_follow(request: Request):
    """Update camera follow."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        camera = cs.update_follow(
            camera_id=body.get("camera_id", ""),
            delta_time=body.get("delta_time", 0.016),
        )
        return camera.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/start-shake")
async def camera_system_start_shake(request: Request):
    """Start camera shake."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        cs.start_shake(
            camera_id=body.get("camera_id", ""),
            amplitude_x=body.get("amplitude_x", 5.0),
            amplitude_y=body.get("amplitude_y", 5.0),
            frequency=body.get("frequency", 10.0),
            duration=body.get("duration", 0.5),
            shake_type=body.get("shake_type", "random"),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/update-shake")
async def camera_system_update_shake(request: Request):
    """Update camera shake."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        cs.update_shake(
            camera_id=body.get("camera_id", ""),
            delta_time=body.get("delta_time", 0.016),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/stop-shake")
async def camera_system_stop_shake(request: Request):
    """Stop camera shake."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        cs.stop_shake(camera_id=body.get("camera_id", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/set-bounds")
async def camera_system_set_bounds(request: Request):
    """Set camera bounds."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system, CameraBounds
        body = await request.json()
        cs = get_camera_system()
        bounds = CameraBounds(
            min_x=body.get("min_x", 0.0),
            min_y=body.get("min_y", 0.0),
            max_x=body.get("max_x", 0.0),
            max_y=body.get("max_y", 0.0),
        )
        cs.set_bounds(
            camera_id=body.get("camera_id", ""),
            bounds=bounds,
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/world-to-screen")
async def camera_system_world_to_screen(request: Request):
    """Convert world to screen coordinates."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        sx, sy = cs.world_to_screen(
            camera_id=body.get("camera_id", ""),
            world_x=body.get("world_x", 0.0),
            world_y=body.get("world_y", 0.0),
        )
        return {"screen_x": sx, "screen_y": sy}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/screen-to-world")
async def camera_system_screen_to_world(request: Request):
    """Convert screen to world coordinates."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        wx, wy = cs.screen_to_world(
            camera_id=body.get("camera_id", ""),
            screen_x=body.get("screen_x", 0.0),
            screen_y=body.get("screen_y", 0.0),
        )
        return {"world_x": wx, "world_y": wy}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/add-effect")
async def camera_system_add_effect(request: Request):
    """Add a camera effect."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        cs.add_effect(
            camera_id=body.get("camera_id", ""),
            name=body.get("name", ""),
            duration=body.get("duration", 1.0),
            params=body.get("params"),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/camera-system/snapshot")
async def camera_system_snapshot(request: Request):
    """Take a camera snapshot."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        body = await request.json()
        cs = get_camera_system()
        snapshot = cs.take_snapshot(camera_id=body.get("camera_id", ""))
        return snapshot.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/camera-system/viewport")
async def camera_system_viewport(request: Request):
    """Get camera viewport."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        cs = get_camera_system()
        return cs.get_camera_viewport(
            camera_id=request.query_params.get("camera_id", ""),
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/camera-system/stats")
async def camera_system_stats():
    """Get camera system statistics."""
    try:
        from sparkai.engine.engine_camera_system import get_camera_system
        cs = get_camera_system()
        return cs.get_camera_stats()
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Animation Controller Routes
# ---------------------------------------------------------------------------

@router.post("/animation-controller/create-clip")
async def animation_controller_create_clip(request: Request):
    """Create an animation clip."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller, AnimationFrame
        body = await request.json()
        ac = get_animation_controller()
        frames = []
        for f in body.get("frames", []):
            frames.append(AnimationFrame(
                frame_index=f.get("frame_index", 0),
                source_rect=f.get("source_rect", [0, 0, 0, 0]),
                duration=f.get("duration", 0.1),
                offset=f.get("offset", [0, 0]),
            ))
        clip = ac.create_clip(
            name=body.get("name", ""),
            frames=frames,
            fps=body.get("fps", 30.0),
            play_mode=body.get("play_mode", "loop"),
        )
        return clip.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/create-machine")
async def animation_controller_create_machine(request: Request):
    """Create an animation state machine."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        result = ac.create_state_machine(
            name=body.get("name", ""),
            default_state=body.get("default_state", "idle"),
        )
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/add-state")
async def animation_controller_add_state(request: Request):
    """Add a state to the state machine."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller, AnimationState
        body = await request.json()
        ac = get_animation_controller()
        state = AnimationState(
            name=body.get("name", ""),
            clip_name=body.get("clip_name", ""),
            speed=body.get("speed", 1.0),
            loop=body.get("loop", True),
            blend_in=body.get("blend_in", 0.15),
            blend_out=body.get("blend_out", 0.15),
        )
        result = ac.add_state(
            machine_id=body.get("machine_id", ""),
            state=state,
        )
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/add-transition")
async def animation_controller_add_transition(request: Request):
    """Add a transition to the state machine."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller, AnimationTransition
        body = await request.json()
        ac = get_animation_controller()
        transition = AnimationTransition(
            from_state=body.get("from_state", ""),
            to_state=body.get("to_state", ""),
            conditions=body.get("conditions", []),
            has_exit_time=body.get("has_exit_time", False),
            exit_time=body.get("exit_time", 0.0),
            duration=body.get("duration", 0.15),
        )
        result = ac.add_transition(
            machine_id=body.get("machine_id", ""),
            transition=transition,
        )
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/add-parameter")
async def animation_controller_add_parameter(request: Request):
    """Add a parameter to the state machine."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller, AnimationParameter
        body = await request.json()
        ac = get_animation_controller()
        param = AnimationParameter(
            name=body.get("name", ""),
            param_type=body.get("param_type", "float"),
            default_value=body.get("default_value", 0.0),
        )
        result = ac.add_parameter(
            machine_id=body.get("machine_id", ""),
            param=param,
        )
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/set-parameter")
async def animation_controller_set_parameter(request: Request):
    """Set a parameter value."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        ac.set_parameter(
            machine_id=body.get("machine_id", ""),
            param_name=body.get("param_name", ""),
            value=body.get("value", 0.0),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/create-instance")
async def animation_controller_create_instance(request: Request):
    """Create an animation state machine instance."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        result = ac.create_instance(machine_id=body.get("machine_id", ""))
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/update-instance")
async def animation_controller_update_instance(request: Request):
    """Update an animation instance."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        instance = ac.update_instance(
            instance_id=body.get("instance_id", ""),
            delta_time=body.get("delta_time", 0.016),
        )
        return instance.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/current-frame")
async def animation_controller_current_frame(request: Request):
    """Get the current animation frame."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        frame = ac.get_current_frame(instance_id=body.get("instance_id", ""))
        return frame.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/pause")
async def animation_controller_pause(request: Request):
    """Pause an animation instance."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        ac.pause_instance(instance_id=body.get("instance_id", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/resume")
async def animation_controller_resume(request: Request):
    """Resume an animation instance."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        ac.resume_instance(instance_id=body.get("instance_id", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/speed")
async def animation_controller_speed(request: Request):
    """Set animation instance speed."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        ac.set_instance_speed(
            instance_id=body.get("instance_id", ""),
            speed=body.get("speed", 1.0),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/animation-controller/trigger-event")
async def animation_controller_trigger_event(request: Request):
    """Trigger a state machine event."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        body = await request.json()
        ac = get_animation_controller()
        ac.trigger_event(
            machine_id=body.get("machine_id", ""),
            event_name=body.get("event_name", ""),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.get("/animation-controller/stats")
async def animation_controller_stats():
    """Get animation controller statistics."""
    try:
        from sparkai.engine.engine_animation_controller import get_animation_controller
        ac = get_animation_controller()
        return ac.get_animation_stats()
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Scene Transition Routes
# ---------------------------------------------------------------------------

@router.post("/scene-transition/register-scene")
async def scene_transition_register_scene(request: Request):
    """Register a scene descriptor."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition, SceneDescriptor
        body = await request.json()
        st = get_scene_transition()
        descriptor = SceneDescriptor(
            id=body.get("id", ""),
            name=body.get("name", ""),
            scene_path=body.get("scene_path", ""),
            transition_in=body.get("transition_in", "fade"),
            transition_out=body.get("transition_out", "fade"),
            is_persistent=body.get("is_persistent", False),
        )
        result = st.register_scene(descriptor)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-transition/load-scene")
async def scene_transition_load_scene(request: Request):
    """Load a scene."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition, TransitionConfig
        body = await request.json()
        st = get_scene_transition()
        config = None
        if body.get("transition_config"):
            tc = body["transition_config"]
            config = TransitionConfig(
                transition_type=tc.get("transition_type", "fade"),
                duration=tc.get("duration", 1.0),
                easing=tc.get("easing", "linear"),
                params=tc.get("params"),
            )
        result = st.load_scene(
            descriptor_id=body.get("descriptor_id", ""),
            load_mode=body.get("load_mode", "single"),
            transition_config=config,
        )
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-transition/transition-to")
async def scene_transition_transition_to(request: Request):
    """Transition to a scene."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition, TransitionConfig
        body = await request.json()
        st = get_scene_transition()
        tc = body.get("config", {})
        config = TransitionConfig(
            transition_type=tc.get("transition_type", "fade"),
            duration=tc.get("duration", 1.0),
            easing=tc.get("easing", "linear"),
            params=tc.get("params"),
        )
        result = st.transition_to(
            from_instance_id=body.get("from_instance_id", ""),
            to_descriptor_id=body.get("to_descriptor_id", ""),
            config=config,
        )
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-transition/update-transition")
async def scene_transition_update_transition(request: Request):
    """Update an active transition."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        body = await request.json()
        st = get_scene_transition()
        result = st.update_transition(
            transition_id=body.get("transition_id", ""),
            delta_time=body.get("delta_time", 0.016),
        )
        if isinstance(result, tuple):
            return {"progress": result[0], "completed": result[1]}
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-transition/cancel-transition")
async def scene_transition_cancel_transition(request: Request):
    """Cancel an active transition."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        body = await request.json()
        st = get_scene_transition()
        st.cancel_transition(transition_id=body.get("transition_id", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-transition/pause-scene")
async def scene_transition_pause_scene(request: Request):
    """Pause a scene instance."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        body = await request.json()
        st = get_scene_transition()
        st.pause_scene(instance_id=body.get("instance_id", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-transition/resume-scene")
async def scene_transition_resume_scene(request: Request):
    """Resume a scene instance."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        body = await request.json()
        st = get_scene_transition()
        st.resume_scene(instance_id=body.get("instance_id", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scene-transition/active-scenes")
async def scene_transition_active_scenes():
    """Get active scenes."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        st = get_scene_transition()
        return st.get_active_scenes()
    except Exception as e:
        return {"error": str(e)}


@router.get("/scene-transition/descriptors")
async def scene_transition_descriptors():
    """Get all scene descriptors."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        st = get_scene_transition()
        return st.get_all_descriptors()
    except Exception as e:
        return {"error": str(e)}


@router.get("/scene-transition/scene-state")
async def scene_transition_scene_state(request: Request):
    """Get a scene instance state."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        st = get_scene_transition()
        return st.get_scene_state(
            instance_id=request.query_params.get("instance_id", ""),
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/scene-transition/stats")
async def scene_transition_stats():
    """Get scene transition statistics."""
    try:
        from sparkai.engine.engine_scene_transition import get_scene_transition
        st = get_scene_transition()
        stats = st.get_scene_stats()
        return stats.to_dict()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Network Replication Routes
# ============================================================

@router.post("/network-replication/register-identity")
async def network_replication_register_identity(request: Request):
    """Register a network-synchronized entity."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication, ReplicationMode
        body = await request.json()
        nr = get_network_replication()
        try:
            mode = ReplicationMode(body.get("replication_mode", "reliable"))
        except ValueError:
            mode = ReplicationMode.RELIABLE
        identity = nr.register_identity(
            entity_type=body.get("entity_type", ""),
            owner_client_id=body.get("owner_client_id", ""),
            is_authoritative=body.get("is_authoritative", True),
            replication_mode=mode,
            spawn_position=tuple(body.get("spawn_position", [0.0, 0.0, 0.0])),
            priority=body.get("priority", 1),
        )
        return identity.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/submit-state")
async def network_replication_submit_state(request: Request):
    """Submit replicated state for a network entity."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        body = await request.json()
        nr = get_network_replication()
        state = nr.submit_state(
            identity_id=body.get("identity_id", ""),
            position=tuple(body.get("position", [0.0, 0.0, 0.0])),
            rotation=tuple(body.get("rotation", [0.0, 0.0, 0.0])),
            velocity=tuple(body.get("velocity", [0.0, 0.0, 0.0])),
            custom_state=body.get("custom_state"),
        )
        return state.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/send-event")
async def network_replication_send_event(request: Request):
    """Send a network event between clients."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication, NetworkEventType
        body = await request.json()
        nr = get_network_replication()
        try:
            etype = NetworkEventType(body.get("event_type", "rpc"))
        except ValueError:
            etype = NetworkEventType.RPC
        event = nr.send_event(
            event_type=etype,
            source_id=body.get("source_id", ""),
            target_id=body.get("target_id", ""),
            payload=body.get("payload", {}),
            reliable=body.get("reliable", True),
        )
        return event.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/register-client")
async def network_replication_register_client(request: Request):
    """Register a client connection."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication, NetworkRole
        body = await request.json()
        nr = get_network_replication()
        try:
            role = NetworkRole(body.get("role", "client"))
        except ValueError:
            role = NetworkRole.CLIENT
        client = nr.register_client(
            address=body.get("address", "127.0.0.1"),
            port=body.get("port", 7777),
            role=role,
        )
        return client.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/heartbeat")
async def network_replication_heartbeat(request: Request):
    """Update client heartbeat timestamp."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        body = await request.json()
        nr = get_network_replication()
        result = nr.update_heartbeat(client_id=body.get("client_id", ""))
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/disconnect")
async def network_replication_disconnect(request: Request):
    """Disconnect a client."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        body = await request.json()
        nr = get_network_replication()
        result = nr.disconnect_client(client_id=body.get("client_id", ""))
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}


@router.get("/network-replication/stats")
async def network_replication_stats():
    """Get network replication statistics."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        nr = get_network_replication()
        return nr.get_stats().to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/network-replication/clients")
async def network_replication_list_clients():
    """List all connected clients."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        nr = get_network_replication()
        return [c.to_dict() for c in nr.list_clients()]
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/interested-entities")
async def network_replication_interested_entities(request: Request):
    """Get entities within a client's view radius (interest management)."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        body = await request.json()
        nr = get_network_replication()
        entities = nr.get_interested_entities(
            client_id=body.get("client_id", ""),
            view_radius=body.get("view_radius", 100.0),
        )
        return [e.to_dict() for e in entities]
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/create-match")
async def network_replication_create_match(request: Request):
    """Create a multiplayer match."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        body = await request.json()
        nr = get_network_replication()
        match = nr.create_match(
            room_name=body.get("room_name", "default"),
            max_players=body.get("max_players", 4),
            game_mode=body.get("game_mode", "free"),
        )
        return match
    except Exception as e:
        return {"error": str(e)}


@router.post("/network-replication/reconcile")
async def network_replication_reconcile(request: Request):
    """Reconcile client-predicted state with server authoritative state."""
    try:
        from sparkai.engine.engine_network_replication import get_network_replication
        body = await request.json()
        nr = get_network_replication()
        result = nr.reconcile_state(
            client_id=body.get("client_id", ""),
            server_state=body.get("server_state", {}),
        )
        return result
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Terrain System Routes
# ============================================================

@router.post("/terrain-system/create-config")
async def terrain_system_create_config(request: Request):
    """Create a terrain generation configuration."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system, TerrainAlgorithm
        body = await request.json()
        ts = get_terrain_system()
        try:
            algo = TerrainAlgorithm(body.get("algorithm", "perlin"))
        except ValueError:
            algo = TerrainAlgorithm.PERLIN
        config = ts.create_config(
            width=body.get("width", 256),
            depth=body.get("depth", 256),
            height_scale=body.get("height_scale", 100.0),
            seed=body.get("seed", 42),
            algorithm=algo,
            octaves=body.get("octaves", 6),
            persistence=body.get("persistence", 0.5),
            lacunarity=body.get("lacunarity", 2.0),
        )
        return config.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/terrain-system/generate")
async def terrain_system_generate(request: Request):
    """Generate terrain from a configuration."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        body = await request.json()
        ts = get_terrain_system()
        chunks = ts.generate_terrain(config_id=body.get("config_id", ""))
        return [c.to_dict() for c in chunks]
    except Exception as e:
        return {"error": str(e)}


@router.get("/terrain-system/height")
async def terrain_system_get_height(
    config_id: str = "",
    world_x: float = 0.0,
    world_z: float = 0.0,
):
    """Sample terrain height at a world position."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        ts = get_terrain_system()
        height = ts.get_height_at(config_id=config_id, world_x=world_x, world_z=world_z)
        return {"height": height, "world_x": world_x, "world_z": world_z}
    except Exception as e:
        return {"error": str(e)}


@router.post("/terrain-system/set-height")
async def terrain_system_set_height(request: Request):
    """Edit terrain height at a world position."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        body = await request.json()
        ts = get_terrain_system()
        result = ts.set_height_at(
            config_id=body.get("config_id", ""),
            world_x=body.get("world_x", 0.0),
            world_z=body.get("world_z", 0.0),
            new_height=body.get("new_height", 0.0),
        )
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/terrain-system/erosion")
async def terrain_system_erosion(request: Request):
    """Apply erosion simulation to terrain."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system, ErosionSettings, ErosionType
        body = await request.json()
        ts = get_terrain_system()
        try:
            etype = ErosionType(body.get("erosion_type", "hydraulic"))
        except ValueError:
            etype = ErosionType.HYDRAULIC
        settings = ErosionSettings(
            erosion_type=etype,
            iterations=body.get("iterations", 100),
            erosion_rate=body.get("erosion_rate", 0.01),
            deposition_rate=body.get("deposition_rate", 0.005),
            evaporation_rate=body.get("evaporation_rate", 0.02),
            rain_amount=body.get("rain_amount", 0.1),
        )
        chunks = ts.apply_erosion(
            config_id=body.get("config_id", ""),
            erosion_settings=settings,
        )
        return [c.to_dict() for c in chunks]
    except Exception as e:
        return {"error": str(e)}


@router.post("/terrain-system/flatten-area")
async def terrain_system_flatten_area(request: Request):
    """Flatten a circular area of terrain."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        body = await request.json()
        ts = get_terrain_system()
        chunks = ts.flatten_area(
            config_id=body.get("config_id", ""),
            center_x=body.get("center_x", 0.0),
            center_z=body.get("center_z", 0.0),
            radius=body.get("radius", 10.0),
        )
        return [c.to_dict() for c in chunks]
    except Exception as e:
        return {"error": str(e)}


@router.post("/terrain-system/raise-area")
async def terrain_system_raise_area(request: Request):
    """Raise a circular area of terrain."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        body = await request.json()
        ts = get_terrain_system()
        chunks = ts.raise_area(
            config_id=body.get("config_id", ""),
            center_x=body.get("center_x", 0.0),
            center_z=body.get("center_z", 0.0),
            radius=body.get("radius", 10.0),
            amount=body.get("amount", 5.0),
        )
        return [c.to_dict() for c in chunks]
    except Exception as e:
        return {"error": str(e)}


@router.post("/terrain-system/generate-island")
async def terrain_system_generate_island(request: Request):
    """Generate an island by masking terrain below sea level."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        body = await request.json()
        ts = get_terrain_system()
        chunks = ts.generate_island(
            config_id=body.get("config_id", ""),
            shore_threshold=body.get("shore_threshold", 0.1),
        )
        return [c.to_dict() for c in chunks]
    except Exception as e:
        return {"error": str(e)}


@router.get("/terrain-system/slope")
async def terrain_system_get_slope(
    config_id: str = "",
    world_x: float = 0.0,
    world_z: float = 0.0,
):
    """Compute terrain slope at a world position."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        ts = get_terrain_system()
        slope = ts.compute_slope_at(config_id=config_id, world_x=world_x, world_z=world_z)
        return {"slope_degrees": slope, "world_x": world_x, "world_z": world_z}
    except Exception as e:
        return {"error": str(e)}


@router.post("/terrain-system/biome")
async def terrain_system_add_biome(request: Request):
    """Add a biome layer to a terrain configuration."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        body = await request.json()
        ts = get_terrain_system()
        from sparkai.engine.engine_terrain_system import BiomeLayer
        biome = BiomeLayer(
            name=body.get("name", "plains"),
            min_height=body.get("min_height", 0.0),
            max_height=body.get("max_height", 100.0),
            base_color=tuple(body.get("base_color", [100, 180, 50, 255])),
            texture_id=body.get("texture_id", ""),
            tree_density=body.get("tree_density", 0.1),
            rock_density=body.get("rock_density", 0.05),
            grass_coverage=body.get("grass_coverage", 0.8),
        )
        config = ts.add_biome_layer(
            config_id=body.get("config_id", ""),
            biome=biome,
        )
        return config.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/terrain-system/stats")
async def terrain_system_stats(config_id: str = ""):
    """Get terrain system statistics."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        ts = get_terrain_system()
        if config_id:
            stats = ts.get_stats(config_id=config_id)
            if stats is None:
                return {"error": f"Terrain config '{config_id}' not found"}
            return stats.to_dict()
        configs = ts.list_configs()
        return {
            "total_configs": len(configs),
            "configs": [c.to_dict() for c in configs],
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/terrain-system/configs")
async def terrain_system_list_configs():
    """List all terrain configurations."""
    try:
        from sparkai.engine.engine_terrain_system import get_terrain_system
        ts = get_terrain_system()
        return [c.to_dict() for c in ts.list_configs()]
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Asset Streamer Routes
# ============================================================

@router.post("/asset-streamer/register-asset")
async def asset_streamer_register_asset(request: Request):
    """Register an asset for streaming."""
    try:
        from sparkai.engine.engine_asset_streamer import get_asset_streamer
        body = await request.json()
        streamer = get_asset_streamer()
        asset = streamer.register_asset(
            asset_path=body.get("asset_path", ""),
            asset_type=body.get("asset_type", "texture"),
            priority=body.get("priority", 1),
            preload=body.get("preload", False),
        )
        return asset.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/asset-streamer/request-load")
async def asset_streamer_request_load(request: Request):
    """Request loading of a streamed asset."""
    try:
        from sparkai.engine.engine_asset_streamer import get_asset_streamer
        body = await request.json()
        streamer = get_asset_streamer()
        result = streamer.request_load(asset_id=body.get("asset_id", ""))
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.get("/asset-streamer/stats")
async def asset_streamer_stats():
    """Get asset streamer statistics."""
    try:
        from sparkai.engine.engine_asset_streamer import get_asset_streamer
        streamer = get_asset_streamer()
        return streamer.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# ECS Entity Component System Routes
# ============================================================

@router.post("/ecs/create-entity")
async def ecs_create_entity(request: Request):
    """Create a new entity in the ECS world."""
    try:
        from sparkai.engine.engine_entity_component_system import get_entity_component_system
        body = await request.json()
        ecs = get_entity_component_system()
        entity = ecs.create_entity(
            name=body.get("name", "Entity"),
            tags=body.get("tags", []),
        )
        return entity.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/ecs/add-component")
async def ecs_add_component(request: Request):
    """Add a component to an entity."""
    try:
        from sparkai.engine.engine_entity_component_system import get_entity_component_system
        body = await request.json()
        ecs = get_entity_component_system()
        result = ecs.add_component(
            entity_id=body.get("entity_id", ""),
            component_type=body.get("component_type", ""),
            component_data=body.get("component_data", {}),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.get("/ecs/entity")
async def ecs_get_entity(entity_id: str = ""):
    """Get an entity by ID."""
    try:
        from sparkai.engine.engine_entity_component_system import get_entity_component_system
        ecs = get_entity_component_system()
        entity = ecs.get_entity(entity_id=entity_id)
        return entity.to_dict() if entity else {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/ecs/query")
async def ecs_query(component_type: str = ""):
    """Query entities with a specific component type."""
    try:
        from sparkai.engine.engine_entity_component_system import get_entity_component_system
        ecs = get_entity_component_system()
        entities = ecs.query_entities(component_type=component_type)
        return [e.to_dict() for e in entities]
    except Exception as e:
        return {"error": str(e)}

@router.get("/ecs/stats")
async def ecs_stats():
    """Get ECS statistics."""
    try:
        from sparkai.engine.engine_entity_component_system import get_entity_component_system
        ecs = get_entity_component_system()
        return ecs.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Scene Manager Routes
# ============================================================

@router.post("/scene-manager/create-scene")
async def scene_manager_create_scene(request: Request):
    """Create a new scene."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        body = await request.json()
        sm = get_scene_manager()
        scene = sm.create_scene(
            name=body.get("name", "New Scene"),
            parent_scene_id=body.get("parent_scene_id"),
        )
        return scene.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/scene-manager/load-scene")
async def scene_manager_load_scene(request: Request):
    """Load a scene."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        body = await request.json()
        sm = get_scene_manager()
        result = sm.load_scene(scene_id=body.get("scene_id", ""))
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/scene-manager/unload-scene")
async def scene_manager_unload_scene(request: Request):
    """Unload a scene."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        body = await request.json()
        sm = get_scene_manager()
        result = sm.unload_scene(scene_id=body.get("scene_id", ""))
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}

@router.get("/scene-manager/scenes")
async def scene_manager_list_scenes():
    """List all scenes."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        sm = get_scene_manager()
        return [s.to_dict() for s in sm.list_scenes()]
    except Exception as e:
        return {"error": str(e)}

@router.get("/scene-manager/stats")
async def scene_manager_stats():
    """Get scene manager statistics."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        sm = get_scene_manager()
        return sm.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Render Pipeline Routes
# ============================================================

@router.post("/render-pipeline/configure")
async def render_pipeline_configure(request: Request):
    """Configure the render pipeline."""
    try:
        from sparkai.engine.engine_render_pipeline import get_render_pipeline
        body = await request.json()
        rp = get_render_pipeline()
        result = rp.configure(
            resolution=tuple(body.get("resolution", [1920, 1080])),
            target_fps=body.get("target_fps", 60),
            vsync=body.get("vsync", True),
            msaa=body.get("msaa", 4),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/render-pipeline/render-frame")
async def render_pipeline_render_frame(request: Request):
    """Render a single frame."""
    try:
        from sparkai.engine.engine_render_pipeline import get_render_pipeline
        body = await request.json()
        rp = get_render_pipeline()
        frame = rp.render_frame(delta_time=body.get("delta_time", 0.016))
        return frame.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.get("/render-pipeline/stats")
async def render_pipeline_stats():
    """Get render pipeline statistics."""
    try:
        from sparkai.engine.engine_render_pipeline import get_render_pipeline
        rp = get_render_pipeline()
        return rp.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Audio System Routes
# ============================================================

@router.post("/audio-system/play-sound")
async def audio_system_play_sound(request: Request):
    """Play a sound effect."""
    try:
        from sparkai.engine.engine_audio_system import get_audio_system
        body = await request.json()
        audio = get_audio_system()
        result = audio.play_sound(
            sound_id=body.get("sound_id", ""),
            volume=body.get("volume", 1.0),
            pitch=body.get("pitch", 1.0),
            loop=body.get("loop", False),
            position=tuple(body.get("position", [0.0, 0.0, 0.0])),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/audio-system/stop-sound")
async def audio_system_stop_sound(request: Request):
    """Stop a playing sound."""
    try:
        from sparkai.engine.engine_audio_system import get_audio_system
        body = await request.json()
        audio = get_audio_system()
        result = audio.stop_sound(instance_id=body.get("instance_id", ""))
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}

@router.post("/audio-system/set-master-volume")
async def audio_system_set_master_volume(request: Request):
    """Set master volume."""
    try:
        from sparkai.engine.engine_audio_system import get_audio_system
        body = await request.json()
        audio = get_audio_system()
        audio.set_master_volume(volume=body.get("volume", 1.0))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.get("/audio-system/stats")
async def audio_system_stats():
    """Get audio system statistics."""
    try:
        from sparkai.engine.engine_audio_system import get_audio_system
        audio = get_audio_system()
        return audio.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Physics Dynamics Routes
# ============================================================

@router.post("/physics-dynamics/apply-force")
async def physics_dynamics_apply_force(request: Request):
    """Apply a force to a physics body."""
    try:
        from sparkai.engine.engine_physics_dynamics import get_physics_dynamics
        body = await request.json()
        pd = get_physics_dynamics()
        result = pd.apply_force(
            body_id=body.get("body_id", ""),
            force=tuple(body.get("force", [0.0, 0.0])),
            point=tuple(body.get("point", [0.0, 0.0])),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/physics-dynamics/set-velocity")
async def physics_dynamics_set_velocity(request: Request):
    """Set velocity of a physics body."""
    try:
        from sparkai.engine.engine_physics_dynamics import get_physics_dynamics
        body = await request.json()
        pd = get_physics_dynamics()
        result = pd.set_velocity(
            body_id=body.get("body_id", ""),
            velocity=tuple(body.get("velocity", [0.0, 0.0])),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.get("/physics-dynamics/stats")
async def physics_dynamics_stats():
    """Get physics dynamics statistics."""
    try:
        from sparkai.engine.engine_physics_dynamics import get_physics_dynamics
        pd = get_physics_dynamics()
        return pd.get_system_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Behavior Orchestrator Routes
# ============================================================

@router.post("/behavior-orchestrator/register-behavior")
async def behavior_orchestrator_register(request: Request):
    """Register a behavior in the orchestrator."""
    try:
        from sparkai.engine.engine_behavior_orchestrator import get_behavior_orchestrator
        body = await request.json()
        bo = get_behavior_orchestrator()
        behavior = bo.register_behavior(
            name=body.get("name", ""),
            entity_id=body.get("entity_id", ""),
            behavior_type=body.get("behavior_type", "state_machine"),
            config=body.get("config", {}),
        )
        return behavior.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/behavior-orchestrator/execute")
async def behavior_orchestrator_execute(request: Request):
    """Execute behavior for an entity."""
    try:
        from sparkai.engine.engine_behavior_orchestrator import get_behavior_orchestrator
        body = await request.json()
        bo = get_behavior_orchestrator()
        result = bo.execute_behavior(
            entity_id=body.get("entity_id", ""),
            delta_time=body.get("delta_time", 0.016),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.get("/behavior-orchestrator/stats")
async def behavior_orchestrator_stats():
    """Get behavior orchestrator statistics."""
    try:
        from sparkai.engine.engine_behavior_orchestrator import get_engine_behavior_orchestrator
        bo = get_engine_behavior_orchestrator()
        return bo.get_orchestration_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Unification Core Routes
# ============================================================

@router.get("/unification-core/stats")
async def unification_core_stats():
    """Get unification core statistics."""
    try:
        from sparkai.engine.engine_unification_core import get_engine_unification_core
        uc = get_engine_unification_core()
        return uc.get_status()
    except Exception as e:
        return {"error": str(e)}

@router.post("/unification-core/register-orchestrator")
async def unification_core_register(request: Request):
    """Register an orchestrator with the unification core."""
    try:
        from sparkai.engine.engine_unification_core import get_engine_unification_core
        body = await request.json()
        uc = get_engine_unification_core()
        result = uc.register_orchestrator(
            name=body.get("name", ""),
            orchestrator_type=body.get("orchestrator_type", ""),
            config=body.get("config", {}),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Deterministic Core Routes
# ============================================================

@router.post("/deterministic-core/record-frame")
async def deterministic_core_record_frame(request: Request):
    """Record a deterministic frame for replay."""
    try:
        from sparkai.engine.engine_deterministic_core import get_deterministic_core
        body = await request.json()
        dc = get_deterministic_core()
        frame = dc.record_frame(
            frame_number=body.get("frame_number", 0),
            inputs=body.get("inputs", {}),
            state_hash=body.get("state_hash", ""),
        )
        return frame.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/deterministic-core/replay")
async def deterministic_core_replay(request: Request):
    """Replay recorded frames."""
    try:
        from sparkai.engine.engine_deterministic_core import get_deterministic_core
        body = await request.json()
        dc = get_deterministic_core()
        result = dc.replay_frames(
            start_frame=body.get("start_frame", 0),
            end_frame=body.get("end_frame", -1),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.get("/deterministic-core/stats")
async def deterministic_core_stats():
    """Get deterministic core statistics."""
    try:
        from sparkai.engine.engine_deterministic_core import get_deterministic_core
        dc = get_deterministic_core()
        return dc.get_status()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Asset Bundler Routes
# ============================================================

@router.post("/asset-bundler/create-bundle")
async def asset_bundler_create_bundle(request: Request):
    """Create an asset bundle."""
    try:
        from sparkai.engine.engine_asset_bundler import get_asset_bundler
        body = await request.json()
        ab = get_asset_bundler()
        bundle = ab.create_bundle(
            name=body.get("name", "bundle"),
            asset_ids=body.get("asset_ids", []),
            compression=body.get("compression", "lz4"),
            platform=body.get("platform", "web"),
        )
        return bundle.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.get("/asset-bundler/stats")
async def asset_bundler_stats():
    """Get asset bundler statistics."""
    try:
        from sparkai.engine.engine_asset_bundler import get_asset_bundler
        ab = get_asset_bundler()
        return ab.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Collision System Routes
# ============================================================

@router.get("/collision-system/stats")
async def collision_system_stats():
    """Get collision system statistics."""
    try:
        from sparkai.engine.engine_collision_system import get_collision_system
        cs = get_collision_system()
        return cs.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/collision-system/create-body")
async def collision_system_create_body(request: Request):
    """Create a collision body."""
    try:
        from sparkai.engine.engine_collision_system import get_collision_system, CollisionShape, CollisionLayer
        body = await request.json()
        cs = get_collision_system()
        shape_str = body.get("shape", "aabb")
        shape = getattr(CollisionShape, shape_str.upper(), CollisionShape.AABB)
        layer_str = body.get("layer", "default")
        layer = getattr(CollisionLayer, layer_str.upper(), CollisionLayer.DEFAULT)
        cb = cs.create_body(
            entity_id=body.get("entity_id", ""),
            shape=shape,
            position=tuple(body.get("position", [0, 0])),
            size=tuple(body.get("size", [1, 1])),
            layer=layer,
            is_static=body.get("is_static", False),
            is_trigger=body.get("is_trigger", False),
        )
        return cb.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/collision-system/raycast")
async def collision_system_raycast(request: Request):
    """Cast a ray and detect collisions."""
    try:
        from sparkai.engine.engine_collision_system import get_collision_system, CollisionLayer
        body = await request.json()
        cs = get_collision_system()
        layer_mask_raw = body.get("layer_mask")
        layer_mask = None
        if layer_mask_raw:
            layer_mask = [getattr(CollisionLayer, lm.upper(), CollisionLayer.DEFAULT) for lm in layer_mask_raw]
        results = cs.raycast(
            origin=tuple(body.get("origin", [0, 0])),
            direction=tuple(body.get("direction", [0, 0])),
            max_distance=body.get("max_distance", 100.0),
            layer_mask=layer_mask,
        )
        return [r.to_dict() for r in results]
    except Exception as e:
        return {"error": str(e)}


@router.post("/collision-system/overlap-area")
async def collision_system_overlap_area(request: Request):
    """Find all bodies overlapping with a given area."""
    try:
        from sparkai.engine.engine_collision_system import get_collision_system, CollisionShape
        body = await request.json()
        cs = get_collision_system()
        shape_str = body.get("shape", "aabb")
        shape = getattr(CollisionShape, shape_str.upper(), CollisionShape.AABB)
        bodies = cs.overlap_area(
            body_id=body.get("body_id", ""),
            shape=shape,
            position=tuple(body.get("position", [0, 0])),
            size=tuple(body.get("size", [1, 1])),
        )
        return [b.to_dict() for b in bodies]
    except Exception as e:
        return {"error": str(e)}


@router.get("/collision-system/body")
async def collision_system_get_body(body_id: str = ""):
    """Get a collision body by ID."""
    try:
        from sparkai.engine.engine_collision_system import get_collision_system
        cs = get_collision_system()
        cb = cs.get_body(body_id)
        return cb.to_dict() if cb else {"error": "Body not found"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Game Loop Routes
# ============================================================

@router.get("/game-loop/stats")
async def game_loop_stats():
    """Get game loop statistics."""
    try:
        from sparkai.engine.engine_game_loop import get_game_loop
        gl = get_game_loop()
        return gl.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/game-loop/start")
async def game_loop_start():
    """Start the game loop."""
    try:
        from sparkai.engine.engine_game_loop import get_game_loop
        gl = get_game_loop()
        gl.start()
        return {"status": "started"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/game-loop/stop")
async def game_loop_stop():
    """Stop the game loop."""
    try:
        from sparkai.engine.engine_game_loop import get_game_loop
        gl = get_game_loop()
        gl.stop()
        return {"status": "stopped"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/game-loop/pause")
async def game_loop_pause():
    """Pause the game loop."""
    try:
        from sparkai.engine.engine_game_loop import get_game_loop
        gl = get_game_loop()
        gl.pause()
        return {"status": "paused"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/game-loop/resume")
async def game_loop_resume():
    """Resume the game loop."""
    try:
        from sparkai.engine.engine_game_loop import get_game_loop
        gl = get_game_loop()
        gl.resume()
        return {"status": "resumed"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/game-loop/frame-timing")
async def game_loop_frame_timing():
    """Get frame timing information."""
    try:
        from sparkai.engine.engine_game_loop import get_game_loop
        gl = get_game_loop()
        timing = gl.get_frame_timing()
        return timing.to_dict()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Resource Cache Routes
# ============================================================

@router.get("/resource-cache/stats")
async def resource_cache_stats():
    """Get resource cache statistics."""
    try:
        from sparkai.engine.engine_resource_cache import get_resource_cache
        rc = get_resource_cache()
        return rc.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/resource-cache/load")
async def resource_cache_load(request: Request):
    """Load a resource into the cache."""
    try:
        from sparkai.engine.engine_resource_cache import get_resource_cache, ResourceType
        body = await request.json()
        rc = get_resource_cache()
        rt_str = body.get("resource_type", "texture")
        resource_type = getattr(ResourceType, rt_str.upper(), ResourceType.TEXTURE)
        handle = rc.load(
            path=body.get("path", ""),
            resource_type=resource_type,
            tags=body.get("tags"),
        )
        return handle.to_dict() if handle else {"error": "Failed to load resource"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/resource-cache/unload")
async def resource_cache_unload(request: Request):
    """Unload a resource from the cache."""
    try:
        from sparkai.engine.engine_resource_cache import get_resource_cache
        body = await request.json()
        rc = get_resource_cache()
        rc.unload(resource_id=body.get("resource_id", ""))
        return {"status": "unloaded"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/resource-cache/resource")
async def resource_cache_get_resource(resource_id: str = ""):
    """Get a cached resource."""
    try:
        from sparkai.engine.engine_resource_cache import get_resource_cache
        rc = get_resource_cache()
        handle = rc.get(resource_id)
        return handle.to_dict() if handle else {"error": "Resource not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/resource-cache/create-group")
async def resource_cache_create_group(request: Request):
    """Create a resource group for batch loading."""
    try:
        from sparkai.engine.engine_resource_cache import get_resource_cache
        body = await request.json()
        rc = get_resource_cache()
        group = rc.create_resource_group(
            name=body.get("name", "group"),
            resource_paths=body.get("resource_paths", []),
            priority=body.get("priority", 0),
        )
        return group.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/resource-cache/load-group")
async def resource_cache_load_group(request: Request):
    """Load all resources in a group."""
    try:
        from sparkai.engine.engine_resource_cache import get_resource_cache
        body = await request.json()
        rc = get_resource_cache()
        rc.load_group(group_id=body.get("group_id", ""))
        return {"status": "group_loaded"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Scene Graph Routes
# ============================================================

@router.get("/scene-graph/stats")
async def scene_graph_stats():
    """Get scene graph statistics."""
    try:
        from sparkai.engine.engine_scene_graph import get_scene_graph
        sg = get_scene_graph()
        return sg.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-graph/create-node")
async def scene_graph_create_node(request: Request):
    """Create a new scene graph node."""
    try:
        from sparkai.engine.engine_scene_graph import get_scene_graph, NodeType, Transform2D
        body = await request.json()
        sg = get_scene_graph()
        nt_str = body.get("node_type", "group")
        node_type = getattr(NodeType, nt_str.upper(), NodeType.GROUP)
        tx_data = body.get("transform")
        transform = None
        if tx_data:
            transform = Transform2D(
                position=tuple(tx_data.get("position", [0, 0])),
                rotation=tx_data.get("rotation", 0.0),
                scale=tuple(tx_data.get("scale", [1, 1])),
            )
        node = sg.create_node(
            name=body.get("name", "Node"),
            node_type=node_type,
            parent_id=body.get("parent_id"),
            transform=transform,
            tags=body.get("tags"),
        )
        return node.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-graph/remove-node")
async def scene_graph_remove_node(request: Request):
    """Remove a node from the scene graph."""
    try:
        from sparkai.engine.engine_scene_graph import get_scene_graph
        body = await request.json()
        sg = get_scene_graph()
        sg.remove_node(node_id=body.get("node_id", ""))
        return {"status": "removed"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scene-graph/node")
async def scene_graph_get_node(node_id: str = ""):
    """Get a scene graph node by ID."""
    try:
        from sparkai.engine.engine_scene_graph import get_scene_graph
        sg = get_scene_graph()
        node = sg.get_node(node_id)
        return node.to_dict() if node else {"error": "Node not found"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scene-graph/find-by-tag")
async def scene_graph_find_by_tag(tag: str = ""):
    """Find scene graph nodes by tag."""
    try:
        from sparkai.engine.engine_scene_graph import get_scene_graph
        sg = get_scene_graph()
        nodes = sg.find_by_tag(tag)
        return [n.to_dict() for n in nodes]
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene-graph/set-parent")
async def scene_graph_set_parent(request: Request):
    """Change the parent of a node."""
    try:
        from sparkai.engine.engine_scene_graph import get_scene_graph
        body = await request.json()
        sg = get_scene_graph()
        sg.set_parent(
            node_id=body.get("node_id", ""),
            new_parent_id=body.get("new_parent_id", ""),
        )
        return {"status": "parent_updated"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Script Engine Routes
# ============================================================

@router.get("/script-engine/stats")
async def script_engine_stats():
    """Get script engine statistics."""
    try:
        from sparkai.engine.engine_script_engine import get_script_engine
        se = get_script_engine()
        return se.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/script-engine/create-binding")
async def script_engine_create_binding(request: Request):
    """Create a script binding for an entity."""
    try:
        from sparkai.engine.engine_script_engine import get_script_engine, ScriptLanguage
        body = await request.json()
        se = get_script_engine()
        lang_str = body.get("language", "python")
        language = getattr(ScriptLanguage, lang_str.upper(), ScriptLanguage.PYTHON)
        binding = se.create_binding(
            entity_id=body.get("entity_id", ""),
            script_source=body.get("script_source", ""),
            language=language,
        )
        return binding.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/script-engine/bind-event")
async def script_engine_bind_event(request: Request):
    """Bind a handler to a script event. Note: handler must be registered separately."""
    try:
        from sparkai.engine.engine_script_engine import get_script_engine, ScriptEvent
        body = await request.json()
        se = get_script_engine()
        event_str = body.get("event", "on_update")
        event = getattr(ScriptEvent, event_str.upper(), ScriptEvent.ON_UPDATE)
        binding = se._bindings.get(body.get("binding_id", ""))
        if not binding:
            return {"error": "Binding not found"}
        se.listen_event(
            entity_id=binding.entity_id,
            event=event,
            binding_id=binding.binding_id,
        )
        return {"status": "event_bound"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/script-engine/execute")
async def script_engine_execute(request: Request):
    """Execute a script binding for a specific event."""
    try:
        from sparkai.engine.engine_script_engine import get_script_engine, ScriptEvent
        body = await request.json()
        se = get_script_engine()
        event_str = body.get("event", "on_update")
        event = getattr(ScriptEvent, event_str.upper(), ScriptEvent.ON_UPDATE)
        se.execute_binding(
            binding_id=body.get("binding_id", ""),
            event=event,
            context=body.get("context"),
        )
        return {"status": "executed"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/script-engine/compile-expression")
async def script_engine_compile_expression(request: Request):
    """Compile a script expression for later evaluation."""
    try:
        from sparkai.engine.engine_script_engine import get_script_engine, ScriptLanguage
        body = await request.json()
        se = get_script_engine()
        lang_str = body.get("language", "python")
        language = getattr(ScriptLanguage, lang_str.upper(), ScriptLanguage.PYTHON)
        expression = se.compile_expression(
            source=body.get("source", ""),
            language=language,
        )
        return expression.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/script-engine/evaluate")
async def script_engine_evaluate(request: Request):
    """Evaluate a compiled expression."""
    try:
        from sparkai.engine.engine_script_engine import get_script_engine
        body = await request.json()
        se = get_script_engine()
        result = se.evaluate(
            expression_id=body.get("expression_id", ""),
            context=body.get("context"),
        )
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Spatial Hash Routes
# ============================================================

@router.get("/spatial-hash/stats")
async def spatial_hash_stats():
    """Get spatial hash statistics."""
    try:
        from sparkai.engine.engine_spatial_hash import get_spatial_hash
        sh = get_spatial_hash()
        return sh.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/spatial-hash/insert")
async def spatial_hash_insert(request: Request):
    """Insert an object into the spatial hash."""
    try:
        from sparkai.engine.engine_spatial_hash import get_spatial_hash
        body = await request.json()
        sh = get_spatial_hash()
        obj = sh.insert(
            entity_id=body.get("entity_id", ""),
            position=tuple(body.get("position", [0.0, 0.0])),
            size=tuple(body.get("size", [1.0, 1.0])),
            layer=body.get("layer", "default"),
            properties=body.get("properties"),
        )
        return obj.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/spatial-hash/update")
async def spatial_hash_update(request: Request):
    """Update an object's position and size in the spatial hash."""
    try:
        from sparkai.engine.engine_spatial_hash import get_spatial_hash
        body = await request.json()
        sh = get_spatial_hash()
        size = body.get("size")
        sh.update(
            object_id=body.get("object_id", ""),
            position=tuple(body.get("position", [0.0, 0.0])),
            size=tuple(size) if size else None,
        )
        return {"status": "updated"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/spatial-hash/query-radius")
async def spatial_hash_query_radius(request: Request):
    """Query objects within a radius of a point."""
    try:
        from sparkai.engine.engine_spatial_hash import get_spatial_hash
        body = await request.json()
        sh = get_spatial_hash()
        results = sh.query_radius(
            center=tuple(body.get("center", [0.0, 0.0])),
            radius=body.get("radius", 1.0),
            layer=body.get("layer"),
            max_results=body.get("max_results", 100),
        )
        return [r.to_dict() for r in results]
    except Exception as e:
        return {"error": str(e)}


@router.post("/spatial-hash/query-rect")
async def spatial_hash_query_rect(request: Request):
    """Query objects within a rectangular region."""
    try:
        from sparkai.engine.engine_spatial_hash import get_spatial_hash
        body = await request.json()
        sh = get_spatial_hash()
        results = sh.query_rect(
            min_x=body.get("min_x", 0.0),
            min_y=body.get("min_y", 0.0),
            max_x=body.get("max_x", 1.0),
            max_y=body.get("max_y", 1.0),
            layer=body.get("layer"),
        )
        return [r.to_dict() for r in results]
    except Exception as e:
        return {"error": str(e)}


@router.get("/spatial-hash/object")
async def spatial_hash_get_object(object_id: str = ""):
    """Get a spatial hash object by ID."""
    try:
        from sparkai.engine.engine_spatial_hash import get_spatial_hash
        sh = get_spatial_hash()
        obj = sh.get_object(object_id)
        return obj.to_dict() if obj else {"error": "Object not found"}
    except Exception as e:
        return {"error": str(e)}


# ===== Game Assembler Routes =====

@router.get("/game-assembler/stats")
async def game_assembler_stats():
    """Get game assembler statistics."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler
        ga = get_game_assembler()
        return {"status": "ok", "stats": ga.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/game-assembler/register-component")
async def game_assembler_register_component(request: Request):
    """Register an engine component."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler, ComponentCategory
        body = await request.json()
        ga = get_game_assembler()
        comp = ga.register_component(
            name=body.get("name", ""),
            category=ComponentCategory(body.get("category", "core")),
            version=body.get("version", "1.0.0"),
            dependencies=body.get("dependencies"),
            provides=body.get("provides"),
            config=body.get("config")
        )
        return {"status": "ok", "component_id": comp.component_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/game-assembler/components")
async def game_assembler_components(category: str = None):
    """List registered components."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler, ComponentCategory
        ga = get_game_assembler()
        cat = ComponentCategory(category) if category else None
        return {"status": "ok", "components": ga.list_components(category=cat)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/game-assembler/add-scene")
async def game_assembler_add_scene(request: Request):
    """Add a scene to the assembler."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler
        body = await request.json()
        ga = get_game_assembler()
        scene = ga.add_scene(
            name=body.get("name", ""),
            entities=body.get("entities"),
            systems=body.get("systems"),
            resources=body.get("resources"),
            config=body.get("config")
        )
        return {"status": "ok", "scene_id": scene.scene_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/game-assembler/scenes")
async def game_assembler_scenes():
    """List all scenes."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler
        ga = get_game_assembler()
        return {"status": "ok", "scenes": ga.list_scenes()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/game-assembler/create-plan")
async def game_assembler_create_plan(request: Request):
    """Create a build plan."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler, BuildTarget
        body = await request.json()
        ga = get_game_assembler()
        plan = ga.create_plan(
            project_name=body.get("project_name", ""),
            target=BuildTarget(body.get("target", "web")),
            component_ids=body.get("component_ids", []),
            scene_ids=body.get("scene_ids")
        )
        return {"status": "ok", "plan_id": plan.plan_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/game-assembler/execute-plan")
async def game_assembler_execute_plan(request: Request):
    """Execute a build plan."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler
        body = await request.json()
        ga = get_game_assembler()
        result = ga.execute_plan(plan_id=body.get("plan_id", ""))
        return {
            "status": "ok",
            "success": result.success,
            "output_path": result.output_path,
            "build_time": result.build_time,
            "warnings": result.warnings,
            "errors": result.errors
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/game-assembler/plans")
async def game_assembler_plans():
    """List all build plans."""
    try:
        from sparkai.engine.engine_game_assembler import get_game_assembler
        ga = get_game_assembler()
        return {"status": "ok", "plans": ga.list_plans()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== AI Bridge Routes =====

@router.get("/ai-bridge/stats")
async def ai_bridge_stats():
    """Get AI bridge statistics."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        return {"status": "ok", "stats": bridge.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-bridge/send-command")
async def ai_bridge_send_command(request: Request):
    """Send a command from agent to engine."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge, CommandType, CommandPriority
        body = await request.json()
        bridge = get_ai_bridge()
        cmd = bridge.send_command(
            command_type=CommandType(body.get("command_type", "spawn_entity")),
            agent_id=body.get("agent_id", ""),
            parameters=body.get("parameters", {}),
            priority=CommandPriority(body.get("priority")) if body.get("priority") else None,
            target_entity=body.get("target_entity", "")
        )
        return {"status": "ok", "command_id": cmd.command_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-bridge/send-event")
async def ai_bridge_send_event(request: Request):
    """Send an event from engine to agent."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge, EventType
        body = await request.json()
        bridge = get_ai_bridge()
        event = bridge.send_event(
            event_type=EventType(body.get("event_type", "entity_created")),
            source_entity=body.get("source_entity", ""),
            target_entity=body.get("target_entity", ""),
            data=body.get("data", {}),
            scene_id=body.get("scene_id", "")
        )
        return {"status": "ok", "event_id": event.event_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/ai-bridge/synced-state")
async def ai_bridge_synced_state():
    """Get synchronized state between agent and engine."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        return {"status": "ok", "state": bridge.get_synced_state()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-bridge/sync-entity")
async def ai_bridge_sync_entity(request: Request):
    """Sync entity state."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        body = await request.json()
        bridge = get_ai_bridge()
        bridge.sync_entity_state(
            entity_id=body.get("entity_id", ""),
            state=body.get("state", {})
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-bridge/record-metric")
async def ai_bridge_record_metric(request: Request):
    """Record a feedback metric."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        body = await request.json()
        bridge = get_ai_bridge()
        metric = bridge.record_metric(
            name=body.get("name", ""),
            value=body.get("value", 0.0),
            category=body.get("category", ""),
            source=body.get("source", "")
        )
        return {"status": "ok", "metric_id": metric.metric_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/ai-bridge/metrics")
async def ai_bridge_metrics(category: str = None, limit: int = 100):
    """Get feedback metrics."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        return {"status": "ok", "metrics": bridge.get_metrics(category=category, limit=limit)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/ai-bridge/metric-summary")
async def ai_bridge_metric_summary():
    """Get metric summary."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        return {"status": "ok", "summary": bridge.get_metric_summary()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/ai-bridge/command-history")
async def ai_bridge_command_history(limit: int = 50):
    """Get command history."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        return {"status": "ok", "commands": bridge.get_command_history(limit=limit)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/ai-bridge/event-history")
async def ai_bridge_event_history(limit: int = 50):
    """Get event history."""
    try:
        from sparkai.engine.engine_ai_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        return {"status": "ok", "events": bridge.get_event_history(limit=limit)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== Render Orchestrator Routes =====

@router.get("/render-orchestrator/stats")
async def render_orchestrator_stats():
    """Get render orchestrator statistics."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator
        ro = get_render_orchestrator()
        return {"status": "ok", "stats": ro.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/render-orchestrator/add-pass")
async def render_orchestrator_add_pass(request: Request):
    """Add a render pass."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator, RenderPassType
        body = await request.json()
        ro = get_render_orchestrator()
        rp = ro.add_render_pass(
            name=body.get("name", ""),
            pass_type=RenderPassType(body.get("pass_type", "opaque_geometry")),
            order=body.get("order", 0),
            dependencies=body.get("dependencies"),
            config=body.get("config")
        )
        return {"status": "ok", "pass_id": rp.pass_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/render-orchestrator/passes")
async def render_orchestrator_passes(pass_type: str = None):
    """List render passes."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator, RenderPassType
        ro = get_render_orchestrator()
        pt = RenderPassType(pass_type) if pass_type else None
        return {"status": "ok", "passes": ro.get_render_passes(pass_type=pt)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/render-orchestrator/sorted-passes")
async def render_orchestrator_sorted_passes():
    """Get topologically sorted render passes."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator
        ro = get_render_orchestrator()
        return {"status": "ok", "order": ro.sort_passes()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/render-orchestrator/set-post-effects")
async def render_orchestrator_set_post_effects(request: Request):
    """Set post-processing effect chain."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator, PostProcessEffect
        body = await request.json()
        ro = get_render_orchestrator()
        effects = [PostProcessEffect(e) for e in body.get("effects", [])]
        ro.set_post_process_chain(effects)
        return {"status": "ok", "chain": ro.get_post_process_chain()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/render-orchestrator/post-effects")
async def render_orchestrator_post_effects():
    """Get current post-processing chain."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator
        ro = get_render_orchestrator()
        return {"status": "ok", "chain": ro.get_post_process_chain()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/render-orchestrator/set-quality")
async def render_orchestrator_set_quality(request: Request):
    """Set quality preset."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator, QualityPreset
        body = await request.json()
        ro = get_render_orchestrator()
        ro.set_quality_preset(QualityPreset(body.get("preset", "high")))
        return {"status": "ok", "quality": ro.get_quality_settings()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/render-orchestrator/record-frame")
async def render_orchestrator_record_frame(request: Request):
    """Record frame statistics."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator
        body = await request.json()
        ro = get_render_orchestrator()
        ro.record_frame(
            draw_calls=body.get("draw_calls", 0),
            triangles=body.get("triangles", 0),
            gpu_time_ms=body.get("gpu_time_ms", 0.0),
            cpu_time_ms=body.get("cpu_time_ms", 0.0),
            pass_times=body.get("pass_times"),
            batch_savings=body.get("batch_savings", 0)
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/render-orchestrator/frame-stats")
async def render_orchestrator_frame_stats():
    """Get recent frame statistics."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator
        ro = get_render_orchestrator()
        return {"status": "ok", "frames": ro.get_frame_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/render-orchestrator/performance")
async def render_orchestrator_performance():
    """Get performance summary."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator
        ro = get_render_orchestrator()
        return {"status": "ok", "performance": ro.get_performance_summary()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/render-orchestrator/gpu-memory")
async def render_orchestrator_gpu_memory():
    """Get GPU memory usage."""
    try:
        from sparkai.engine.engine_render_orchestrator import get_render_orchestrator
        ro = get_render_orchestrator()
        return {"status": "ok", "memory": ro.get_gpu_memory_usage()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# AI Game Runtime Routes
# ============================================================

@router.get("/ai-game-runtime/stats")
async def ai_game_runtime_stats():
    """Get AI Game Runtime system statistics."""
    try:
        from sparkai.engine.engine_ai_game_runtime import get_ai_game_runtime
        instance = get_ai_game_runtime()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-game-runtime/register-agent")
async def ai_game_runtime_register_agent(body: dict):
    """Register a game agent."""
    try:
        from sparkai.engine.engine_ai_game_runtime import get_ai_game_runtime
        instance = get_ai_game_runtime()
        instance.register_agent(
            agent_id=body.get("agent_id"),
            name=body.get("name"),
            metadata=body.get("metadata")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-game-runtime/add-hook")
async def ai_game_runtime_add_hook(body: dict):
    """Add a hook callback for an agent."""
    try:
        from sparkai.engine.engine_ai_game_runtime import get_ai_game_runtime
        instance = get_ai_game_runtime()
        instance.add_hook(
            agent_id=body.get("agent_id"),
            hook_type=body.get("hook_type"),
            callback_name=body.get("callback_name"),
            priority=body.get("priority", 0)
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-game-runtime/submit-action")
async def ai_game_runtime_submit_action(body: dict):
    """Submit an agent action."""
    try:
        from sparkai.engine.engine_ai_game_runtime import get_ai_game_runtime
        instance = get_ai_game_runtime()
        instance.submit_action(
            agent_id=body.get("agent_id"),
            action_type=body.get("action_type"),
            target=body.get("target"),
            parameters=body.get("parameters")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/ai-game-runtime/pending-actions")
async def ai_game_runtime_pending_actions():
    """Get pending agent actions."""
    try:
        from sparkai.engine.engine_ai_game_runtime import get_ai_game_runtime
        instance = get_ai_game_runtime()
        return {"status": "ok", "actions": instance.get_pending_actions()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ai-game-runtime/execute-hooks")
async def ai_game_runtime_execute_hooks(body: dict):
    """Execute hooks for a given hook type."""
    try:
        from sparkai.engine.engine_ai_game_runtime import get_ai_game_runtime
        instance = get_ai_game_runtime()
        instance.execute_hooks(
            hook_type=body.get("hook_type"),
            game_state=body.get("game_state")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Procedural Gameplay Routes
# ============================================================

@router.get("/procedural-gameplay/stats")
async def procedural_gameplay_stats():
    """Get Procedural Gameplay system statistics."""
    try:
        from sparkai.engine.engine_procedural_gameplay import get_procedural_gameplay
        instance = get_procedural_gameplay()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/procedural-gameplay/create-session")
async def procedural_gameplay_create_session(body: dict):
    """Create a new procedural gameplay session."""
    try:
        from sparkai.engine.engine_procedural_gameplay import get_procedural_gameplay
        instance = get_procedural_gameplay()
        session = instance.create_session(
            style=body.get("style"),
            difficulty=body.get("difficulty"),
            player_level=body.get("player_level"),
            seed=body.get("seed")
        )
        return {"status": "ok", "session": session}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/procedural-gameplay/generate-mechanic")
async def procedural_gameplay_generate_mechanic(body: dict):
    """Generate a gameplay mechanic."""
    try:
        from sparkai.engine.engine_procedural_gameplay import get_procedural_gameplay
        instance = get_procedural_gameplay()
        mechanic = instance.generate_mechanic(
            session_id=body.get("session_id"),
            type=body.get("type"),
            difficulty_tier=body.get("difficulty_tier")
        )
        return {"status": "ok", "mechanic": mechanic}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/procedural-gameplay/generate-event")
async def procedural_gameplay_generate_event(body: dict):
    """Generate a gameplay event."""
    try:
        from sparkai.engine.engine_procedural_gameplay import get_procedural_gameplay
        instance = get_procedural_gameplay()
        event = instance.generate_event(
            session_id=body.get("session_id"),
            trigger_condition=body.get("trigger_condition"),
            mechanic_count=body.get("mechanic_count")
        )
        return {"status": "ok", "event": event}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/procedural-gameplay/generate-encounter")
async def procedural_gameplay_generate_encounter(body: dict):
    """Generate a gameplay encounter."""
    try:
        from sparkai.engine.engine_procedural_gameplay import get_procedural_gameplay
        instance = get_procedural_gameplay()
        encounter = instance.generate_encounter(
            session_id=body.get("session_id"),
            difficulty=body.get("difficulty"),
            style=body.get("style")
        )
        return {"status": "ok", "encounter": encounter}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/procedural-gameplay/adapt-difficulty")
async def procedural_gameplay_adapt_difficulty(body: dict):
    """Adapt difficulty based on player performance."""
    try:
        from sparkai.engine.engine_procedural_gameplay import get_procedural_gameplay
        instance = get_procedural_gameplay()
        result = instance.adapt_difficulty(
            session_id=body.get("session_id"),
            player_performance=body.get("player_performance")
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Animation System Routes
# ============================================================

@router.get("/animation-system/stats")
async def animation_system_stats():
    """Get Animation System statistics."""
    try:
        from sparkai.engine.engine_animation_system import get_animation_system
        instance = get_animation_system()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/animation-system/create-animation")
async def animation_system_create_animation(body: dict):
    """Create a new animation."""
    try:
        from sparkai.engine.engine_animation_system import get_animation_system
        instance = get_animation_system()
        result = instance.create_animation(
            name=body.get("name"),
            duration=body.get("duration"),
            keyframes=body.get("keyframes")
        )
        return {"status": "ok", "animation": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/animation-system/list")
async def animation_system_list():
    """List all animations."""
    try:
        from sparkai.engine.engine_animation_system import get_animation_system
        instance = get_animation_system()
        return {"status": "ok", "animations": instance.list_animations()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Camera Controller Routes
# ============================================================

@router.get("/camera-controller/stats")
async def camera_controller_stats():
    """Get Camera Controller system statistics."""
    try:
        from sparkai.engine.engine_camera_controller import get_camera_controller
        instance = get_camera_controller()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/camera-controller/create")
async def camera_controller_create(body: dict):
    """Create a new camera."""
    try:
        from sparkai.engine.engine_camera_controller import get_camera_controller
        instance = get_camera_controller()
        result = instance.create(
            name=body.get("name"),
            position=body.get("position"),
            target=body.get("target"),
            fov=body.get("fov")
        )
        return {"status": "ok", "camera": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/camera-controller/move")
async def camera_controller_move(body: dict):
    """Move a camera to a new position."""
    try:
        from sparkai.engine.engine_camera_controller import get_camera_controller
        instance = get_camera_controller()
        instance.move(
            camera_id=body.get("camera_id"),
            position=body.get("position")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Particle Emitter Routes
# ============================================================

@router.get("/particle-emitter/stats")
async def particle_emitter_stats():
    """Get Particle Emitter system statistics."""
    try:
        from sparkai.engine.engine_particle_emitter import get_particle_emitter
        instance = get_particle_emitter()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/particle-emitter/create")
async def particle_emitter_create(body: dict):
    """Create a new particle emitter."""
    try:
        from sparkai.engine.engine_particle_emitter import get_particle_emitter
        instance = get_particle_emitter()
        result = instance.create(
            name=body.get("name"),
            config=body.get("config")
        )
        return {"status": "ok", "emitter": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Pathfinding Routes
# ============================================================

@router.get("/pathfinding/stats")
async def pathfinding_stats():
    """Get Pathfinding system statistics."""
    try:
        from sparkai.engine.engine_pathfinding import get_pathfinding_engine
        instance = get_pathfinding_engine()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/pathfinding/find-path")
async def pathfinding_find_path(body: dict):
    """Find a path between two points on a grid."""
    try:
        from sparkai.engine.engine_pathfinding import get_pathfinding_engine
        instance = get_pathfinding_engine()
        path = instance.find_path(
            start=body.get("start"),
            end=body.get("end"),
            grid=body.get("grid")
        )
        return {"status": "ok", "path": path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# State Machine Routes
# ============================================================

@router.get("/state-machine/stats")
async def state_machine_stats():
    """Get State Machine system statistics."""
    try:
        from sparkai.engine.engine_state_machine import get_state_machine_engine
        instance = get_state_machine_engine()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/state-machine/create")
async def state_machine_create(body: dict):
    """Create a new state machine."""
    try:
        from sparkai.engine.engine_state_machine import get_state_machine_engine
        instance = get_state_machine_engine()
        result = instance.create(
            name=body.get("name"),
            states=body.get("states"),
            transitions=body.get("transitions")
        )
        return {"status": "ok", "state_machine": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Physics World 2D Routes
# ============================================================

@router.get("/physics-world-2d/stats")
async def physics_world_2d_stats():
    """Get Physics World 2D system statistics."""
    try:
        from sparkai.engine.engine_physics_world_2d import get_engine_physics_world_2d
        instance = get_engine_physics_world_2d()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/physics-world-2d/create-world")
async def physics_world_2d_create_world(body: dict):
    """Create a new 2D physics world."""
    try:
        from sparkai.engine.engine_physics_world_2d import get_engine_physics_world_2d
        instance = get_engine_physics_world_2d()
        result = instance.create_world(
            gravity=body.get("gravity"),
            bounds=body.get("bounds")
        )
        return {"status": "ok", "world": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Visual Scripting Routes
# ============================================================

@router.get("/visual-scripting/stats")
async def visual_scripting_stats():
    """Get Visual Scripting system statistics."""
    try:
        from sparkai.engine.engine_visual_scripting import get_engine_visual_scripting
        instance = get_engine_visual_scripting()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/visual-scripting/create-script")
async def visual_scripting_create_script(body: dict):
    """Create a new visual script."""
    try:
        from sparkai.engine.engine_visual_scripting import get_engine_visual_scripting
        instance = get_engine_visual_scripting()
        result = instance.create_script(
            name=body.get("name"),
            nodes=body.get("nodes"),
            connections=body.get("connections")
        )
        return {"status": "ok", "script": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Procedural World Routes
# ============================================================

@router.get("/procedural-world/stats")
async def procedural_world_stats():
    """Get Procedural World system statistics."""
    try:
        from sparkai.engine.engine_procedural_world import get_procedural_world
        instance = get_procedural_world()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/procedural-world/generate")
async def procedural_world_generate(body: dict):
    """Generate a procedural world."""
    try:
        from sparkai.engine.engine_procedural_world import get_procedural_world
        instance = get_procedural_world()
        result = instance.generate(
            size=body.get("size"),
            seed=body.get("seed"),
            biome=body.get("biome")
        )
        return {"status": "ok", "world": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Tilemap System Routes
# ============================================================

@router.get("/tilemap-system/stats")
async def tilemap_system_stats():
    """Get Tilemap System statistics."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        instance = get_tilemap_system()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/tilemap-system/create")
async def tilemap_system_create(body: dict):
    """Create a new tilemap."""
    try:
        from sparkai.engine.engine_tilemap_system import get_tilemap_system
        instance = get_tilemap_system()
        result = instance.create(
            name=body.get("name"),
            width=body.get("width"),
            height=body.get("height"),
            tile_size=body.get("tile_size")
        )
        return {"status": "ok", "tilemap": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Audio Spatial Routes
# ============================================================

@router.get("/audio-spatial/stats")
async def audio_spatial_stats():
    """Get Audio Spatial system statistics."""
    try:
        from sparkai.engine.engine_audio_spatial import get_audio_spatial
        instance = get_audio_spatial()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/audio-spatial/create-source")
async def audio_spatial_create_source(body: dict):
    """Create a spatial audio source."""
    try:
        from sparkai.engine.engine_audio_spatial import get_audio_spatial
        instance = get_audio_spatial()
        result = instance.create_source(
            name=body.get("name"),
            position=body.get("position"),
            sound=body.get("sound")
        )
        return {"status": "ok", "source": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Sprite Animator Routes
# ============================================================

@router.get("/sprite-animator/stats")
async def sprite_animator_stats():
    """Get Sprite Animator system statistics."""
    try:
        from sparkai.engine.engine_sprite_animator import get_sprite_animator
        instance = get_sprite_animator()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/sprite-animator/create")
async def sprite_animator_create(body: dict):
    """Create a new sprite animation."""
    try:
        from sparkai.engine.engine_sprite_animator import get_sprite_animator
        instance = get_sprite_animator()
        result = instance.create(
            name=body.get("name"),
            frames=body.get("frames"),
            fps=body.get("fps")
        )
        return {"status": "ok", "animation": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Navmesh Forge Routes
# ============================================================

@router.get("/navmesh-forge/stats")
async def navmesh_forge_stats():
    """Get Navmesh Forge system statistics."""
    try:
        from sparkai.engine.engine_navmesh_forge import get_navmesh_forge
        instance = get_navmesh_forge()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/navmesh-forge/generate")
async def navmesh_forge_generate(body: dict):
    """Generate a navigation mesh."""
    try:
        from sparkai.engine.engine_navmesh_forge import get_navmesh_forge
        instance = get_navmesh_forge()
        result = instance.generate(
            geometry=body.get("geometry"),
            agent_radius=body.get("agent_radius")
        )
        return {"status": "ok", "navmesh": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# GPU Batch Rendering Routes
# ============================================================

@router.get("/gpu-batch-rendering/stats")
async def gpu_batch_rendering_stats():
    """Get GPU Batch Rendering system statistics."""
    try:
        from sparkai.engine.engine_gpu_batch_rendering import get_gpu_batch_rendering
        instance = get_gpu_batch_rendering()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/gpu-batch-rendering/add-batch")
async def gpu_batch_rendering_add_batch(body: dict):
    """Add a new batch rendering group."""
    try:
        from sparkai.engine.engine_gpu_batch_rendering import get_gpu_batch_rendering
        instance = get_gpu_batch_rendering()
        instance.add_batch(
            name=body.get("name"),
            material=body.get("material"),
            max_instances=body.get("max_instances")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Deterministic Recorder Routes
# ============================================================

@router.get("/deterministic-recorder/stats")
async def deterministic_recorder_stats():
    """Get Deterministic Recorder system statistics."""
    try:
        from sparkai.engine.engine_deterministic_recorder import get_deterministic_recorder
        instance = get_deterministic_recorder()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/deterministic-recorder/start-recording")
async def deterministic_recorder_start_recording(body: dict):
    """Start a recording session."""
    try:
        from sparkai.engine.engine_deterministic_recorder import get_deterministic_recorder
        instance = get_deterministic_recorder()
        result = instance.start_recording(
            session_name=body.get("session_name")
        )
        return {"status": "ok", "session": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/deterministic-recorder/stop-recording")
async def deterministic_recorder_stop_recording(body: dict):
    """Stop a recording session."""
    try:
        from sparkai.engine.engine_deterministic_recorder import get_deterministic_recorder
        instance = get_deterministic_recorder()
        instance.stop_recording(
            session_id=body.get("session_id")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Signal Bus Routes
# ============================================================

@router.get("/signal-bus/stats")
async def signal_bus_stats():
    """Get Signal Bus system statistics."""
    try:
        from sparkai.engine.engine_signal_bus import get_signal_bus
        instance = get_signal_bus()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/signal-bus/emit")
async def signal_bus_emit(body: dict):
    """Emit a signal to the bus."""
    try:
        from sparkai.engine.engine_signal_bus import get_signal_bus
        instance = get_signal_bus()
        instance.emit(
            signal_name=body.get("signal_name"),
            data=body.get("data")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Entity Blueprint Routes
# ============================================================

@router.get("/entity-blueprint/stats")
async def entity_blueprint_stats():
    """Get Entity Blueprint system statistics."""
    try:
        from sparkai.engine.engine_entity_blueprint import get_entity_blueprint
        instance = get_entity_blueprint()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/entity-blueprint/create")
async def entity_blueprint_create(body: dict):
    """Create a new entity blueprint."""
    try:
        from sparkai.engine.engine_entity_blueprint import get_entity_blueprint
        instance = get_entity_blueprint()
        result = instance.create(
            name=body.get("name"),
            components=body.get("components")
        )
        return {"status": "ok", "blueprint": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Post Processing Routes
# ============================================================

@router.get("/post-processing/stats")
async def post_processing_stats():
    """Get Post Processing system statistics."""
    try:
        from sparkai.engine.engine_post_processing import get_post_processing
        instance = get_post_processing()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/post-processing/add-effect")
async def post_processing_add_effect(body: dict):
    """Add a post-processing effect."""
    try:
        from sparkai.engine.engine_post_processing import get_post_processing
        instance = get_post_processing()
        instance.add_effect(
            name=body.get("name"),
            effect_type=body.get("effect_type"),
            parameters=body.get("parameters")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Asset Streamer Routes
# ============================================================

@router.get("/asset-streamer/stats")
async def asset_streamer_stats():
    """Get Asset Streamer system statistics."""
    try:
        from sparkai.engine.engine_asset_streamer import get_asset_streamer
        instance = get_asset_streamer()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/asset-streamer/load")
async def asset_streamer_load(body: dict):
    """Load an asset with priority."""
    try:
        from sparkai.engine.engine_asset_streamer import get_asset_streamer
        instance = get_asset_streamer()
        result = instance.load(
            asset_path=body.get("asset_path"),
            priority=body.get("priority")
        )
        return {"status": "ok", "asset": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Scene Manager Routes
# ============================================================

@router.get("/scene-manager/stats")
async def scene_manager_stats():
    """Get Scene Manager system statistics."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        instance = get_scene_manager()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/scene-manager/create-scene")
async def scene_manager_create_scene(body: dict):
    """Create a new scene."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        instance = get_scene_manager()
        result = instance.create_scene(
            name=body.get("name"),
            entities=body.get("entities")
        )
        return {"status": "ok", "scene": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/scene-manager/load-scene")
async def scene_manager_load_scene(body: dict):
    """Load a scene by ID."""
    try:
        from sparkai.engine.engine_scene_manager import get_scene_manager
        instance = get_scene_manager()
        instance.load_scene(
            scene_id=body.get("scene_id")
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Game State Analyzer Routes
# ============================================================

@router.get("/game-state-analyzer/stats")
async def game_state_analyzer_stats():
    """Get Game State Analyzer system statistics."""
    try:
        from sparkai.engine.engine_game_state_analyzer import get_game_state_analyzer
        instance = get_game_state_analyzer()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/game-state-analyzer/analyze")
async def game_state_analyzer_analyze(body: dict):
    """Analyze a game state."""
    try:
        from sparkai.engine.engine_game_state_analyzer import get_game_state_analyzer
        instance = get_game_state_analyzer()
        result = instance.analyze(
            state_data=body.get("state_data")
        )
        return {"status": "ok", "analysis": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Live Feedback Routes
# ============================================================

@router.get("/live-feedback/stats")
async def live_feedback_stats():
    """Get live feedback engine statistics."""
    try:
        from sparkai.engine.engine_live_feedback import get_engine_live_feedback
        instance = get_engine_live_feedback()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/live-feedback/analyze-entity")
async def live_feedback_analyze_entity(request: Request):
    """Analyze an entity for feedback."""
    try:
        from sparkai.engine.engine_live_feedback import get_engine_live_feedback
        body = await request.json()
        instance = get_engine_live_feedback()
        items = instance.analyze_entity(
            entity_id=body.get("entity_id", ""),
            entity_data=body.get("entity_data", {})
        )
        return {"status": "ok", "feedback": [item.to_dict() for item in items]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/live-feedback/analyze-scene")
async def live_feedback_analyze_scene(request: Request):
    """Analyze a scene for feedback."""
    try:
        from sparkai.engine.engine_live_feedback import get_engine_live_feedback
        body = await request.json()
        instance = get_engine_live_feedback()
        items = instance.analyze_scene(
            scene_id=body.get("scene_id", ""),
            scene_data=body.get("scene_data", {})
        )
        return {"status": "ok", "feedback": [item.to_dict() for item in items]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/live-feedback/analyze-project")
async def live_feedback_analyze_project(request: Request):
    """Analyze a project for feedback."""
    try:
        from sparkai.engine.engine_live_feedback import get_engine_live_feedback
        body = await request.json()
        instance = get_engine_live_feedback()
        items = instance.analyze_project(project_data=body.get("project_data", {}))
        return {"status": "ok", "feedback": [item.to_dict() for item in items]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/live-feedback/analyze-runtime")
async def live_feedback_analyze_runtime(request: Request):
    """Analyze runtime metrics for feedback."""
    try:
        from sparkai.engine.engine_live_feedback import get_engine_live_feedback
        body = await request.json()
        instance = get_engine_live_feedback()
        items = instance.analyze_runtime(runtime_metrics=body.get("runtime_metrics", {}))
        return {"status": "ok", "feedback": [item.to_dict() for item in items]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/live-feedback/feedback")
async def live_feedback_get_feedback(request: Request):
    """Get feedback items with filters."""
    try:
        from sparkai.engine.engine_live_feedback import get_engine_live_feedback
        instance = get_engine_live_feedback()
        items = instance.get_feedback(
            category=request.query_params.get("category"),
            severity=request.query_params.get("severity"),
            scope=request.query_params.get("scope"),
            applied=request.query_params.get("applied")
        )
        return {"status": "ok", "feedback": [item.to_dict() for item in items[:50]]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/live-feedback/apply-fix")
async def live_feedback_apply_fix(request: Request):
    """Apply an auto-fix for a feedback item."""
    try:
        from sparkai.engine.engine_live_feedback import get_engine_live_feedback
        body = await request.json()
        instance = get_engine_live_feedback()
        success = instance.apply_fix(feedback_id=body.get("feedback_id", ""))
        return {"status": "ok", "applied": success}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Asset Pipeline Routes
# ============================================================

@router.get("/asset-pipeline/stats")
async def asset_pipeline_stats():
    """Get asset pipeline statistics."""
    try:
        from sparkai.engine.engine_asset_pipeline import get_asset_pipeline_engine
        instance = get_asset_pipeline_engine()
        return {"status": "ok", "stats": instance.get_stats()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/asset-pipeline/create-style-profile")
async def asset_pipeline_create_style(request: Request):
    """Create a style profile."""
    try:
        from sparkai.engine.engine_asset_pipeline import get_asset_pipeline_engine
        body = await request.json()
        instance = get_asset_pipeline_engine()
        profile = instance.create_style_profile(
            name=body.get("name", ""),
            color_palette=body.get("color_palette", ["#000000", "#ffffff"]),
            theme=body.get("theme", "fantasy"),
            mood=body.get("mood", "neutral"),
            art_style=body.get("art_style", "pixel"),
            resolution=body.get("resolution", "1080p"),
            pixel_scale=body.get("pixel_scale", 1)
        )
        return {"status": "ok", "profile": profile.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/asset-pipeline/request-asset")
async def asset_pipeline_request_asset(request: Request):
    """Request asset generation."""
    try:
        from sparkai.engine.engine_asset_pipeline import get_asset_pipeline_engine
        body = await request.json()
        instance = get_asset_pipeline_engine()
        req = instance.request_asset(
            asset_type=body.get("asset_type", "sprite"),
            name=body.get("name", ""),
            style_profile_id=body.get("style_profile_id", ""),
            parameters=body.get("parameters", {})
        )
        return {"status": "ok", "request": req.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/asset-pipeline/generate-asset")
async def asset_pipeline_generate_asset(request: Request):
    """Generate an asset from a request."""
    try:
        from sparkai.engine.engine_asset_pipeline import get_asset_pipeline_engine
        body = await request.json()
        instance = get_asset_pipeline_engine()
        asset = instance.generate_asset(request_id=body.get("request_id", ""))
        return {"status": "ok", "asset": asset.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/asset-pipeline/style-profiles")
async def asset_pipeline_style_profiles():
    """List all style profiles."""
    try:
        from sparkai.engine.engine_asset_pipeline import get_asset_pipeline_engine
        instance = get_asset_pipeline_engine()
        profiles = instance.list_style_profiles()
        return {"status": "ok", "profiles": [p.to_dict() for p in profiles]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/asset-pipeline/assets")
async def asset_pipeline_assets(request: Request):
    """List generated assets with filters."""
    try:
        from sparkai.engine.engine_asset_pipeline import get_asset_pipeline_engine
        instance = get_asset_pipeline_engine()
        assets = instance.list_assets(
            asset_type=request.query_params.get("asset_type"),
            style_profile_id=request.query_params.get("style_profile_id")
        )
        return {"status": "ok", "assets": [a.to_dict() for a in assets]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/asset-pipeline/batch-generate")
async def asset_pipeline_batch_generate(request: Request):
    """Batch generate assets."""
    try:
        from sparkai.engine.engine_asset_pipeline import get_asset_pipeline_engine
        body = await request.json()
        instance = get_asset_pipeline_engine()
        assets = instance.batch_generate(body.get("requests", []))
        return {"status": "ok", "assets": [a.to_dict() for a in assets]}
    except Exception as e:
        return {"status": "error", "message": str(e)}