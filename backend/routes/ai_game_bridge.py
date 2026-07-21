"""
SparkLabs Backend - AI-Native Game Bridge API Routes

REST API endpoints for the AiNativeGameBridge. The bridge connects live
HTML5 games running in the browser to the server-side CognitiveGameEngine,
enabling real-time AI observation and adaptation of running games.

Endpoints:
  POST /game-bridge/sessions            - Start a new bridge session
  GET  /game-bridge/sessions            - List active sessions
  GET  /game-bridge/sessions/{id}       - Get session status
  POST /game-bridge/sessions/{id}/telemetry - Receive a telemetry frame
  GET  /game-bridge/sessions/{id}/directives - Get pending directives
  GET  /game-bridge/sessions/{id}/history    - Get frame history
  POST /game-bridge/sessions/{id}/pause - Pause a session
  POST /game-bridge/sessions/{id}/resume - Resume a session
  POST /game-bridge/sessions/{id}/end   - End a session
  DELETE /game-bridge/sessions/{id}     - Delete a session
  GET  /game-bridge/status              - Get bridge status
  POST /game-bridge/reset               - Reset the bridge
  POST /game-bridge/simulate            - Simulate a telemetry stream
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from sparkai.engine.engine_ai_native_game_bridge import (
    AiNativeGameBridge,
    parse_telemetry_frame,
)

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class StartSessionRequest(BaseModel):
    game_id: str = ""
    game_title: str = ""
    genre: str = ""
    player_id: str = ""


class TelemetryRequest(BaseModel):
    tick: int = 0
    timestamp: Optional[float] = None
    player: Dict[str, Any] = {}
    events: List[str] = []
    score: int = 0
    lives: int = 3
    level: int = 1
    enemy_count: int = 0
    collectible_count: int = 0


class SimulateRequest(BaseModel):
    frames: int = 60
    goal_x: float = 800.0
    strategy: str = "speedrun"  # speedrun, cautious, random


# =============================================================================
# Helper
# =============================================================================

def _bridge() -> AiNativeGameBridge:
    return AiNativeGameBridge.get_instance()


def _ok(data: Any) -> Dict[str, Any]:
    return {"status": "success", "data": data}


def _err(msg: str, code: int = 404) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={"status": "error", "error": msg},
    )


# =============================================================================
# Session Routes
# =============================================================================

@router.post("/sessions")
async def start_session(req: StartSessionRequest):
    """Start a new bridge session for a live game."""
    session = _bridge().start_session(
        game_id=req.game_id,
        game_title=req.game_title,
        genre=req.genre,
        player_id=req.player_id,
    )
    return _ok(session.to_dict())


@router.get("/sessions")
async def list_sessions(only_active: bool = True):
    """List all bridge sessions."""
    sessions = _bridge().list_sessions(only_active=only_active)
    return _ok([s.to_dict() for s in sessions])


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a bridge session's status."""
    status = _bridge().session_status(session_id)
    if status is None:
        return _err("session not found")
    return _ok(status)


@router.post("/sessions/{session_id}/telemetry")
async def post_telemetry(session_id: str, req: TelemetryRequest):
    """Receive a telemetry frame from the client game."""
    import time as _time
    frame = parse_telemetry_frame({
        "tick": req.tick,
        "timestamp": req.timestamp if req.timestamp is not None else _time.time(),
        "player": req.player,
        "events": req.events,
        "score": req.score,
        "lives": req.lives,
        "level": req.level,
        "enemy_count": req.enemy_count,
        "collectible_count": req.collectible_count,
    })
    result = _bridge().ingest_telemetry(session_id, frame)
    if result.get("status") == "error":
        return _err(result.get("error", "unknown"), code=400)
    return _ok(result)


@router.get("/sessions/{session_id}/directives")
async def get_directives(session_id: str, limit: int = 8):
    """Get pending directives for a session."""
    directives = _bridge().get_directives(session_id, limit=limit)
    return _ok([d.to_dict() for d in directives])


@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str, limit: int = 30):
    """Get the frame history for a session."""
    history = _bridge().session_history(session_id, limit=limit)
    return _ok(history)


@router.post("/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """Pause a bridge session."""
    if not _bridge().pause_session(session_id):
        return _err("session not found")
    return _ok({"session_id": session_id, "status": "paused"})


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """Resume a paused bridge session."""
    if not _bridge().resume_session(session_id):
        return _err("session not found")
    return _ok({"session_id": session_id, "status": "active"})


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str):
    """End a bridge session."""
    if not _bridge().end_session(session_id):
        return _err("session not found")
    return _ok({"session_id": session_id, "status": "ended"})


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a bridge session."""
    if not _bridge().delete_session(session_id):
        return _err("session not found")
    return _ok({"session_id": session_id, "deleted": True})


# =============================================================================
# Bridge Status
# =============================================================================

@router.get("/status")
async def bridge_status():
    """Get the overall bridge status."""
    return _ok(_bridge().status())


@router.post("/reset")
async def reset_bridge():
    """Reset the bridge (clears all sessions)."""
    _bridge().reset()
    return _ok({"reset": True})


# =============================================================================
# Simulation Endpoint
# =============================================================================

@router.post("/simulate")
async def simulate_telemetry(req: SimulateRequest):
    """
    Simulate a stream of telemetry frames for testing. Creates a new
    session, generates synthetic player movement, and returns the
    session's final status with all directives produced.
    """
    import time as _time
    bridge = _bridge()
    session = bridge.start_session(
        game_id="simulated",
        game_title="Bridge Simulation",
        genre="platformer",
        player_id="virtual_player",
    )
    session_id = session.session_id

    frames_run = 0
    player_x = 100.0
    player_y = 464.0
    player_vx = 0.0
    player_vy = 0.0
    on_ground = True
    jumps_remaining = 1
    health = 100.0
    score = 0
    goal_x = req.goal_x
    strategy = req.strategy

    start_time = _time.time()
    directives_total = 0

    for tick in range(1, req.frames + 1):
        # Strategy-based virtual player
        if strategy == "speedrun":
            player_vx = 4.2
            if on_ground and tick % 30 == 0:
                player_vy = -10.0
                on_ground = False
                jumps_remaining = 0
        elif strategy == "cautious":
            player_vx = 2.5
            if on_ground and tick % 45 == 0:
                player_vy = -9.0
                on_ground = False
                jumps_remaining = 0
        elif strategy == "random":
            import random
            player_vx = random.uniform(-2, 4)
            if on_ground and random.random() < 0.05:
                player_vy = -10.0
                on_ground = False
                jumps_remaining = 0

        # Apply physics
        player_vy += 0.55
        if player_vy > 16:
            player_vy = 16
        player_x += player_vx
        player_y += player_vy
        if player_y >= 464.0:
            player_y = 464.0
            player_vy = 0.0
            on_ground = True
            jumps_remaining = 1

        # Track events
        events = []
        if not on_ground and player_vy < 0:
            events.append("jump")

        # Occasionally simulate a death and respawn
        if tick % 80 == 0 and strategy != "cautious":
            events.append("death")
            health = max(0, health - 25)
            if health <= 0:
                health = 100.0
                player_x = max(100.0, player_x - 50)
            score = max(0, score - 10)

        # Collectibles
        if tick % 25 == 0:
            events.append("collect")
            score += 50

        # Enemy kills
        if tick % 50 == 0 and strategy in ("speedrun", "aggressive"):
            events.append("enemy_kill")
            score += 100

        frame = parse_telemetry_frame({
            "tick": tick,
            "timestamp": start_time + tick * (1.0 / 60.0),
            "player": {
                "x": player_x,
                "y": player_y,
                "vx": player_vx,
                "vy": player_vy,
                "health": health,
                "on_ground": on_ground,
                "wall_sliding": False,
                "jumps_remaining": jumps_remaining,
            },
            "events": events,
            "score": score,
            "lives": 3,
            "level": 1,
            "enemy_count": 2,
            "collectible_count": 5,
        })
        result = bridge.ingest_telemetry(session_id, frame)
        directives_total += len(result.get("directives", []))
        frames_run += 1

        if player_x >= goal_x:
            break

    final_status = bridge.session_status(session_id) or {}
    return _ok({
        "session_id": session_id,
        "frames_run": frames_run,
        "directives_produced": directives_total,
        "reached_goal": player_x >= goal_x,
        "final_player_x": player_x,
        "goal_x": goal_x,
        "final_score": score,
        "session": final_status,
    })
