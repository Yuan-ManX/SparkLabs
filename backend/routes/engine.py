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
