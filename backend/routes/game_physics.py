"""
SparkLabs Backend - Game Physics API Routes

REST API endpoints for the server-side 2D physics engine. The physics
world mirrors the client-side physics in generated games, enabling the
cognitive layer to simulate game states, predict action outcomes, and
test parameter changes before applying them to live games.

Endpoints:
  GET  /game-physics/status       - Physics world status and body list
  POST /game-physics/step         - Step the physics world by one timestep
  POST /game-physics/step-batch   - Step the physics world N times
  POST /game-physics/simulate     - Run a batch simulation and return trajectory
  POST /game-physics/predict      - Predict the outcome of an action
  POST /game-physics/start        - Start the physics world
  POST /game-physics/pause        - Pause the physics world
  POST /game-physics/resume       - Resume a paused physics world
  POST /game-physics/reset        - Reset the physics world to default scene
  GET  /game-physics/bodies       - List all physics bodies
  GET  /game-physics/collisions   - List recent collision events
  POST /game-physics/config       - Update physics configuration
  POST /game-physics/scene        - Load a scene preset (platformer, parkour, etc.)
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class StepRequest(BaseModel):
    left: bool = False
    right: bool = False
    jump_pressed: bool = False
    jump_held: bool = False
    up: bool = False
    down: bool = False
    shoot: bool = False
    dt: Optional[float] = None


class StepBatchRequest(BaseModel):
    inputs: List[StepRequest] = []
    count: int = 10
    dt: Optional[float] = None


class SimulateRequest(BaseModel):
    inputs: List[StepRequest] = []
    ticks: int = 60
    return_trajectory: bool = True


class PredictRequest(BaseModel):
    action_type: str = "jump"  # jump, move_left, move_right, wall_jump, double_jump
    ticks: int = 30
    params: Optional[Dict[str, Any]] = None


class ConfigUpdateRequest(BaseModel):
    gravity: Optional[float] = None
    jump_strength: Optional[float] = None
    move_speed: Optional[float] = None
    wall_slide_speed: Optional[float] = None
    wall_jump_kickback: Optional[float] = None
    coyote_frames: Optional[int] = None
    jump_buffer_frames: Optional[int] = None
    can_wall_jump: Optional[bool] = None
    can_double_jump: Optional[bool] = None
    variable_jump_cutoff: Optional[float] = None
    air_control: Optional[float] = None
    ground_friction: Optional[float] = None
    air_friction: Optional[float] = None


class SceneRequest(BaseModel):
    scene_name: str = "platformer"  # platformer, parkour, empty


# =============================================================================
# Helper
# =============================================================================

def _get_world():
    from sparkai.engine.engine_game_physics import PhysicsWorld
    return PhysicsWorld.get_instance()


def _input_from_request(req: StepRequest):
    from sparkai.engine.engine_game_physics import InputState
    return InputState(
        left=req.left,
        right=req.right,
        jump_pressed=req.jump_pressed,
        jump_held=req.jump_held,
        up=req.up,
        down=req.down,
        shoot=req.shoot,
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/game-physics/status")
async def game_physics_status():
    """Get the physics world status, including body count and player state."""
    try:
        world = _get_world()
        return JSONResponse({"status": "success", "data": world.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/step")
async def game_physics_step(req: StepRequest):
    """Step the physics world by one fixed timestep with the given input."""
    try:
        world = _get_world()
        inp = _input_from_request(req)
        result = world.step(dt=req.dt, input_state=inp)
        player = world.get_player()
        return JSONResponse({
            "status": "success",
            "data": {
                "tick": result.tick,
                "collisions": result.collisions,
                "bodies_moved": result.bodies_moved,
                "player_on_ground": result.player_on_ground,
                "player_wall_sliding": result.player_wall_sliding,
                "player_position": {
                    "x": player.position.x, "y": player.position.y,
                } if player else None,
                "player_velocity": {
                    "x": player.velocity.x, "y": player.velocity.y,
                } if player else None,
                "duration_s": result.duration_s,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/step-batch")
async def game_physics_step_batch(req: StepBatchRequest):
    """Step the physics world N times. If inputs is provided, each input
    is applied in sequence; otherwise default input is used for each step."""
    try:
        world = _get_world()
        count = max(1, min(req.count if not req.inputs else len(req.inputs), 500))
        results = []
        for i in range(count):
            if req.inputs and i < len(req.inputs):
                inp = _input_from_request(req.inputs[i])
            else:
                from sparkai.engine.engine_game_physics import InputState
                inp = InputState()
            r = world.step(dt=req.dt, input_state=inp)
            results.append({
                "tick": r.tick,
                "collisions": r.collisions,
                "player_on_ground": r.player_on_ground,
                "player_wall_sliding": r.player_wall_sliding,
            })
        player = world.get_player()
        return JSONResponse({
            "status": "success",
            "data": {
                "steps_run": len(results),
                "results": results[-20:],  # last 20 to keep payload small
                "final_player_position": {
                    "x": player.position.x, "y": player.position.y,
                } if player else None,
                "final_player_velocity": {
                    "x": player.velocity.x, "y": player.velocity.y,
                } if player else None,
                "world_status": world.status(),
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/simulate")
async def game_physics_simulate(req: SimulateRequest):
    """Run a batch simulation and return the trajectory of all bodies.
    Does not modify the live world state (uses prediction)."""
    try:
        world = _get_world()
        ticks = max(1, min(req.ticks, 500))
        # Build input sequence
        from sparkai.engine.engine_game_physics import InputState
        inputs = []
        for i in range(ticks):
            if req.inputs and i < len(req.inputs):
                inputs.append(_input_from_request(req.inputs[i]))
            else:
                inputs.append(InputState())

        # Use predict_trajectory to get non-destructive trajectory
        trajectory = world.predict_trajectory(
            body_id="player", ticks=ticks,
            input_state=inputs[0] if inputs else None,
        )

        # Also run simulate to get telemetry
        sim_results = world.simulate(ticks=ticks, input_sequence=inputs)
        total_collisions = sum(r.collisions for r in sim_results)
        wall_slide_ticks = sum(1 for r in sim_results if r.player_wall_sliding)
        on_ground_ticks = sum(1 for r in sim_results if r.player_on_ground)

        return JSONResponse({
            "status": "success",
            "data": {
                "ticks_simulated": len(sim_results),
                "total_collisions": total_collisions,
                "wall_slide_ticks": wall_slide_ticks,
                "on_ground_ticks": on_ground_ticks,
                "trajectory": [
                    {"x": p.x, "y": p.y} for p in trajectory
                ] if req.return_trajectory else [],
                "start_position": {
                    "x": trajectory[0].x, "y": trajectory[0].y,
                } if trajectory else None,
                "final_position": {
                    "x": trajectory[-1].x, "y": trajectory[-1].y,
                } if trajectory else None,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/predict")
async def game_physics_predict(req: PredictRequest):
    """Predict the outcome of a named action (jump, move_left, move_right,
    wall_jump, double_jump) by simulating it in the physics world."""
    try:
        from sparkai.engine.engine_cognitive_game_engine import get_cognitive_engine
        engine = get_cognitive_engine()
        ticks = max(1, min(req.ticks, 200))
        result = engine.predict_action_outcome(
            action_type=req.action_type,
            params=req.params,
            ticks=ticks,
        )
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/start")
async def game_physics_start():
    """Start the physics world (sets state to RUNNING)."""
    try:
        world = _get_world()
        world.start()
        return JSONResponse({
            "status": "success",
            "data": {"state": world._state.value},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/pause")
async def game_physics_pause():
    """Pause the physics world."""
    try:
        world = _get_world()
        world.pause()
        return JSONResponse({
            "status": "success",
            "data": {"state": world._state.value},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/resume")
async def game_physics_resume():
    """Resume a paused physics world."""
    try:
        world = _get_world()
        world.resume()
        return JSONResponse({
            "status": "success",
            "data": {"state": world._state.value},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/reset")
async def game_physics_reset():
    """Reset the physics world to the default scene."""
    try:
        world = _get_world()
        world.load_default_scene()
        world.start()
        return JSONResponse({"status": "success", "data": world.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/game-physics/bodies")
async def game_physics_bodies():
    """List all physics bodies with their current state."""
    try:
        world = _get_world()
        with world._lock:
            bodies = []
            for body in world._bodies.values():
                bodies.append(body.to_dict())
        return JSONResponse({
            "status": "success",
            "data": {"bodies": bodies, "count": len(bodies)},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/game-physics/collisions")
async def game_physics_collisions(limit: int = 20):
    """List recent collision events."""
    try:
        world = _get_world()
        limit = max(1, min(limit, 100))
        with world._lock:
            events = list(world._collision_history)[-limit:]
        return JSONResponse({
            "status": "success",
            "data": {
                "collisions": [
                    {
                        "body_a": e.body_a_id,
                        "body_b": e.body_b_id,
                        "side": e.side.value,
                        "penetration": e.penetration,
                        "tick": e.tick,
                    } for e in events
                ],
                "count": len(events),
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/config")
async def game_physics_update_config(req: ConfigUpdateRequest):
    """Update physics configuration parameters. Only provided fields are updated."""
    try:
        world = _get_world()
        with world._lock:
            config = world._config
            if req.gravity is not None:
                config.gravity = req.gravity
            if req.jump_strength is not None:
                config.jump_strength = req.jump_strength
            if req.move_speed is not None:
                config.move_speed = req.move_speed
            if req.wall_slide_speed is not None:
                config.wall_slide_speed = req.wall_slide_speed
            if req.wall_jump_kickback is not None:
                config.wall_jump_kickback = req.wall_jump_kickback
            if req.coyote_frames is not None:
                config.coyote_frames = req.coyote_frames
            if req.jump_buffer_frames is not None:
                config.jump_buffer_frames = req.jump_buffer_frames
            if req.can_wall_jump is not None:
                config.can_wall_jump = req.can_wall_jump
            if req.can_double_jump is not None:
                config.can_double_jump = req.can_double_jump
            if req.variable_jump_cutoff is not None:
                config.variable_jump_cutoff = req.variable_jump_cutoff
            if req.air_control is not None:
                config.air_control = req.air_control
            if req.ground_friction is not None:
                config.ground_friction = req.ground_friction
            if req.air_friction is not None:
                config.air_friction = req.air_friction
        return JSONResponse({
            "status": "success",
            "data": {"config": world._config.to_dict()},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-physics/scene")
async def game_physics_load_scene(req: SceneRequest):
    """Load a scene preset into the physics world."""
    try:
        world = _get_world()
        if req.scene_name == "platformer":
            world.load_default_scene()
        elif req.scene_name == "empty":
            world.reset()
        else:
            world.load_default_scene()
        world.start()
        return JSONResponse({
            "status": "success",
            "data": {
                "scene": req.scene_name,
                "world_status": world.status(),
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )
