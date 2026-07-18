"""
SparkLabs Backend - Game Critic API Routes

REST API endpoints for the AI Game Critic that automatically
evaluates game quality across 10 dimensions and produces
professional review reports with findings and recommendations.

Endpoints:
  GET    /game-critic/status                       - Critic status
  GET    /game-critic/stats                        - Aggregate statistics
  GET    /game-critic/snapshot                     - Point-in-time snapshot
  GET    /game-critic/sessions                     - List review sessions
  POST   /game-critic/sessions                     - Create a review session
  GET    /game-critic/sessions/{session_id}        - Get a session
  PATCH  /game-critic/sessions/{session_id}        - Update a session
  POST   /game-critic/sessions/{session_id}/complete - Complete a session
  POST   /game-critic/sessions/{session_id}/scores - Score a dimension
  GET    /game-critic/sessions/{session_id}/scores - List scores
  GET    /game-critic/sessions/{session_id}/overall-score - Overall score
  POST   /game-critic/sessions/{session_id}/findings - Add a finding
  GET    /game-critic/sessions/{session_id}/findings - List findings
  POST   /game-critic/sessions/{session_id}/recommendations - Add recommendation
  GET    /game-critic/sessions/{session_id}/recommendations - List recommendations
  POST   /game-critic/sessions/{session_id}/report - Generate a report
  GET    /game-critic/reports                      - List reports
  GET    /game-critic/reports/{report_id}          - Get a report
  POST   /game-critic/comparisons                  - Compare two sessions
  GET    /game-critic/comparisons                  - List comparisons
  GET    /game-critic/events                       - List audit events
  POST   /game-critic/reset                        - Reset to seed state
  POST   /game-critic/critique                     - Auto-critique HTML game
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _critic():
    """Lazily import and return the GameCriticAgent singleton."""
    from sparkai.agent.agent_game_critic import get_game_critic
    return get_game_critic()


@router.get("/game-critic/status")
async def critic_status():
    """Get the Game Critic status."""
    try:
        return JSONResponse({"status": "success", "data": _critic().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/stats")
async def critic_stats():
    """Get aggregate statistics."""
    try:
        return JSONResponse({"status": "success", "data": _critic().get_stats().to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/snapshot")
async def critic_snapshot():
    """Get a point-in-time snapshot."""
    try:
        return JSONResponse({"status": "success", "data": _critic().get_snapshot().to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/sessions")
async def critic_list_sessions(status: str = ""):
    """List review sessions, optionally filtered by status."""
    try:
        from sparkai.agent.agent_game_critic import ReviewStatus
        status_filter = ReviewStatus(status) if status else None
        sessions = _critic().list_sessions(status=status_filter)
        return JSONResponse({
            "status": "success",
            "data": [s.to_dict() for s in sessions],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/sessions")
async def critic_create_session(request: Request):
    """Create a new review session."""
    try:
        body = await request.json()
        session = _critic().create_session(
            game_title=body.get("game_title", "Untitled Game"),
            build_version=body.get("build_version", ""),
            reviewer=body.get("reviewer", "AI Critic"),
            genre=body.get("genre", ""),
            platform=body.get("platform", ""),
            tags=body.get("tags"),
            notes=body.get("notes", ""),
        )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/sessions/{session_id}")
async def critic_get_session(session_id: str):
    """Get a single review session."""
    try:
        session = _critic().get_session(session_id)
        if session is None:
            return JSONResponse(
                {"status": "error", "message": "session not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.patch("/game-critic/sessions/{session_id}")
async def critic_update_session(session_id: str, request: Request):
    """Update a review session's mutable fields."""
    try:
        body = await request.json()
        session = _critic().update_session(session_id, body)
        if session is None:
            return JSONResponse(
                {"status": "error", "message": "session not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/sessions/{session_id}/complete")
async def critic_complete_session(session_id: str):
    """Mark a review session as completed."""
    try:
        session = _critic().complete_session(session_id)
        if session is None:
            return JSONResponse(
                {"status": "error", "message": "session not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": session.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/sessions/{session_id}/scores")
async def critic_score_criterion(session_id: str, request: Request):
    """Assign a score to a review dimension."""
    try:
        from sparkai.agent.agent_game_critic import ReviewDimension
        body = await request.json()
        dimension = ReviewDimension(body.get("dimension", ""))
        score = float(body.get("score", 0.0))
        notes = body.get("notes", "")
        result = _critic().score_criterion(session_id, dimension, score, notes)
        if result is None:
            return JSONResponse(
                {"status": "error", "message": "session not found or capacity reached"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/sessions/{session_id}/scores")
async def critic_get_scores(session_id: str):
    """Get all criterion scores for a session."""
    try:
        scores = _critic().get_scores(session_id)
        return JSONResponse({
            "status": "success",
            "data": [s.to_dict() for s in scores],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/sessions/{session_id}/overall-score")
async def critic_get_overall_score(session_id: str):
    """Compute the weighted overall score for a session."""
    try:
        score = _critic().get_overall_score(session_id)
        return JSONResponse({
            "status": "success",
            "data": {"session_id": session_id, "overall_score": score},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/sessions/{session_id}/findings")
async def critic_add_finding(session_id: str, request: Request):
    """Add a qualitative finding to a review session."""
    try:
        from sparkai.agent.agent_game_critic import (
            FindingCategory, SeverityLevel, ReviewDimension,
        )
        body = await request.json()
        finding = _critic().add_finding(
            session_id,
            FindingCategory(body.get("category", "observation")),
            SeverityLevel(body.get("severity", "info")),
            ReviewDimension(body.get("dimension", "polish")),
            body.get("title", ""),
            body.get("description", ""),
            body.get("location", ""),
        )
        if finding is None:
            return JSONResponse(
                {"status": "error", "message": "session not found or capacity reached"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": finding.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/sessions/{session_id}/findings")
async def critic_list_findings(
    session_id: str,
    category: str = "",
    dimension: str = "",
):
    """List findings for a session, optionally filtered."""
    try:
        from sparkai.agent.agent_game_critic import (
            FindingCategory, ReviewDimension,
        )
        cat_filter = FindingCategory(category) if category else None
        dim_filter = ReviewDimension(dimension) if dimension else None
        findings = _critic().list_findings(session_id, cat_filter, dim_filter)
        return JSONResponse({
            "status": "success",
            "data": [f.to_dict() for f in findings],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/sessions/{session_id}/recommendations")
async def critic_add_recommendation(session_id: str, request: Request):
    """Add an actionable recommendation to a review session."""
    try:
        from sparkai.agent.agent_game_critic import ReviewDimension
        body = await request.json()
        rec = _critic().add_recommendation(
            session_id,
            ReviewDimension(body.get("dimension", "polish")),
            int(body.get("priority", 3)),
            body.get("title", ""),
            body.get("description", ""),
            body.get("linked_finding_ids"),
            body.get("estimated_effort", ""),
        )
        if rec is None:
            return JSONResponse(
                {"status": "error", "message": "session not found or capacity reached"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": rec.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/sessions/{session_id}/recommendations")
async def critic_list_recommendations(session_id: str, dimension: str = ""):
    """List recommendations for a session, optionally filtered by dimension."""
    try:
        from sparkai.agent.agent_game_critic import ReviewDimension
        dim_filter = ReviewDimension(dimension) if dimension else None
        recs = _critic().list_recommendations(session_id, dim_filter)
        return JSONResponse({
            "status": "success",
            "data": [r.to_dict() for r in recs],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/sessions/{session_id}/report")
async def critic_generate_report(session_id: str):
    """Generate a comprehensive review report for a session."""
    try:
        report = _critic().generate_report(session_id)
        if report is None:
            return JSONResponse(
                {"status": "error", "message": "session not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": report.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/reports")
async def critic_list_reports(limit: int = 50):
    """List recent reports."""
    try:
        reports = _critic().list_reports(limit=limit)
        return JSONResponse({
            "status": "success",
            "data": [r.to_dict() for r in reports],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/reports/{report_id}")
async def critic_get_report(report_id: str):
    """Get a stored report by ID."""
    try:
        report = _critic().get_report(report_id)
        if report is None:
            return JSONResponse(
                {"status": "error", "message": "report not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": report.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/comparisons")
async def critic_compare_sessions(request: Request):
    """Compare two review sessions side by side."""
    try:
        body = await request.json()
        session_a_id = body.get("session_a_id", "")
        session_b_id = body.get("session_b_id", "")
        if not session_a_id or not session_b_id:
            return JSONResponse(
                {"status": "error", "message": "session_a_id and session_b_id are required"},
                status_code=400,
            )
        comparison = _critic().compare_sessions(session_a_id, session_b_id)
        if comparison is None:
            return JSONResponse(
                {"status": "error", "message": "one or both sessions not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": comparison.to_dict()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/comparisons")
async def critic_list_comparisons(limit: int = 50):
    """List recent comparisons."""
    try:
        comparisons = _critic().list_comparisons(limit=limit)
        return JSONResponse({
            "status": "success",
            "data": [c.to_dict() for c in comparisons],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-critic/events")
async def critic_list_events(limit: int = 100):
    """List recent audit events."""
    try:
        events = _critic().list_events(limit=limit)
        return JSONResponse({
            "status": "success",
            "data": [e.to_dict() for e in events],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/reset")
async def critic_reset():
    """Reset the critic to seed state."""
    try:
        _critic().reset()
        return JSONResponse({"status": "success", "data": {"reset": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-critic/critique")
async def critic_auto_critique(request: Request):
    """Automatically critique a game from its HTML source.

    Body:
      html: str          - The game HTML to analyze
      game_title: str    - Optional title for the review
      build_version: str - Optional build version
      genre: str         - Optional genre hint
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        if not html:
            return JSONResponse(
                {"status": "error", "message": "html is required"},
                status_code=400,
            )
        result = _critic().critique_game(
            html=html,
            game_title=body.get("game_title", "Untitled Game"),
            build_version=body.get("build_version", "auto-1.0.0"),
            genre=body.get("genre", ""),
            reviewer=body.get("reviewer", "AI Critic"),
        )
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
