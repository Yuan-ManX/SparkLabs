"""
SparkLabs Backend - Event Sheet Synthesizer API Routes

REST API endpoints for the AI Event Sheet Synthesizer that converts
natural-language game logic into executable EventSheet structures.

Endpoints:
  GET  /event-sheet/status       - Synthesizer status and runtime stats
  POST /event-sheet/synthesize   - Synthesize an event sheet from text
  GET  /event-sheet/history      - List recent synthesis sessions
  GET  /event-sheet/runtime      - EventSheetRuntime stats and sheet list
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/event-sheet/status")
async def event_sheet_status():
    """Get the Event Sheet Synthesizer status."""
    try:
        from sparkai.agent.agent_event_sheet_synthesizer import get_event_sheet_synthesizer
        synth = get_event_sheet_synthesizer()
        if not synth._initialized:
            synth.initialize()
        return JSONResponse({"status": "success", "data": synth.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/event-sheet/synthesize")
async def event_sheet_synthesize(request: Request):
    """Synthesize an event sheet from a natural-language description.

    Body:
      prompt: str        - Natural-language game logic
      sheet_name: str    - Optional name for the generated sheet
      linked_scene: str  - Optional scene identifier
    """
    try:
        from sparkai.agent.agent_event_sheet_synthesizer import get_event_sheet_synthesizer
        body = await request.json()
        prompt = body.get("prompt", "").strip()
        sheet_name = body.get("sheet_name", "")
        linked_scene = body.get("linked_scene", "")

        if not prompt:
            return JSONResponse(
                {"status": "error", "message": "prompt is required"},
                status_code=400,
            )

        synth = get_event_sheet_synthesizer()
        if not synth._initialized:
            synth.initialize()

        result = synth.synthesize(
            prompt=prompt,
            sheet_name=sheet_name,
            linked_scene=linked_scene,
        )
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/event-sheet/history")
async def event_sheet_history():
    """List recent synthesis sessions."""
    try:
        from sparkai.agent.agent_event_sheet_synthesizer import get_event_sheet_synthesizer
        synth = get_event_sheet_synthesizer()
        if not synth._initialized:
            synth.initialize()
        return JSONResponse({"status": "success", "data": synth.get_history()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/event-sheet/runtime")
async def event_sheet_runtime():
    """Get EventSheetRuntime stats and registered sheets."""
    try:
        from sparkai.engine.engine_event_sheet import get_event_sheet
        runtime = get_event_sheet()
        stats = runtime.get_stats()
        return JSONResponse({"status": "success", "data": stats})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
