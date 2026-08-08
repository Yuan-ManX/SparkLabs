"""
SparkLabs Backend - Game Runtime API Routes

REST API endpoints for managing game session lifecycle:
creation, start, pause, resume, stop, and destroy.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CreateSessionRequest(BaseModel):
    prompt: str = ""
    html: str = ""
    genre_hint: Optional[str] = None
    fps: int = 60


class SessionActionRequest(BaseModel):
    session_id: str


@router.get("/runtime/status")
async def runtime_status():
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        return JSONResponse({"status": "success", "data": runtime.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/runtime/sessions")
async def list_sessions(state: Optional[str] = None):
    try:
        from sparkai.agent.game_runtime import get_game_runtime, GameState
        runtime = get_game_runtime()
        state_enum = None
        if state:
            state_enum = GameState(state)
        return JSONResponse({
            "status": "success",
            "data": runtime.list_sessions(state=state_enum),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/runtime/sessions")
async def create_session(req: CreateSessionRequest):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()

        if req.prompt:
            session = runtime.create_from_prompt(
                req.prompt, genre_hint=req.genre_hint
            )
        else:
            session = runtime.create_session(
                prompt=req.prompt,
                html=req.html,
                fps=req.fps,
            )
        return JSONResponse({
            "status": "success",
            "data": session.to_dict(),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/runtime/sessions/{session_id}")
async def get_session(session_id: str):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        session = runtime.get_session(session_id)
        if not session:
            return JSONResponse(
                {"status": "error", "message": f"Session {session_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/runtime/sessions/{session_id}/html")
async def get_session_html(session_id: str):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        html = runtime.get_session_html(session_id)
        if not html:
            return JSONResponse(
                {"status": "error", "message": f"No HTML for session {session_id}"},
                status_code=404,
            )
        return Response(content=html, media_type="text/html")
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/runtime/sessions/{session_id}/start")
async def start_session(session_id: str):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        session = runtime.start_session(session_id)
        if not session:
            return JSONResponse(
                {"status": "error", "message": f"Session {session_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/runtime/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        session = runtime.pause_session(session_id)
        if not session:
            return JSONResponse(
                {"status": "error", "message": f"Session {session_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/runtime/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        session = runtime.resume_session(session_id)
        if not session:
            return JSONResponse(
                {"status": "error", "message": f"Session {session_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/runtime/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        session = runtime.stop_session(session_id)
        if not session:
            return JSONResponse(
                {"status": "error", "message": f"Session {session_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/runtime/sessions/{session_id}")
async def destroy_session(session_id: str):
    try:
        from sparkai.agent.game_runtime import get_game_runtime
        runtime = get_game_runtime()
        ok = runtime.destroy_session(session_id)
        if not ok:
            return JSONResponse(
                {"status": "error", "message": f"Session {session_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": {"destroyed": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
