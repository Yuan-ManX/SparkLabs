"""
SparkLabs Backend - Agent Game Synthesizer API Routes

REST API endpoints that bridge the GameContentSynthesizer (AI content
generation) with the GameRuntime (playable HTML production). This is
the canonical "describe a game, get a playable game" pipeline.

Endpoints:
  GET  /game-synthesizer/status         -> pipeline status
  POST /game-synthesizer/synthesize     -> produce a GameDesignDocument (JSON)
  POST /game-synthesizer/generate       -> full pipeline: prompt -> playable HTML
  POST /game-synthesizer/build          -> build HTML from an existing result_id
  GET  /game-synthesizer/genres         -> list supported genres
  GET  /game-synthesizer/result/{id}    -> fetch a previous synthesis result
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request / Response Models
# =============================================================================


class SynthesizeRequest(BaseModel):
    prompt: str
    genre_hint: Optional[str] = None
    character_count: int = 12
    level_count_hint: Optional[int] = None


class GenerateRequest(BaseModel):
    prompt: str
    genre_hint: Optional[str] = None
    character_count: int = 12
    level_count_hint: Optional[int] = None
    return_html: bool = True


class BuildRequest(BaseModel):
    result_id: str
    return_html: bool = True


# =============================================================================
# In-memory result cache (for retrieval by result_id)
# =============================================================================

# Stores synthesis results and built games keyed by result_id.
# Sized to avoid unbounded memory growth during long-running sessions.
_RESULT_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_MAX = 50


def _cache_result(result_id: str, data: Dict[str, Any]) -> None:
    """Store a result in the cache, evicting oldest entries when full."""
    if len(_RESULT_CACHE) >= _CACHE_MAX:
        # Evict the oldest entry (first key)
        oldest = next(iter(_RESULT_CACHE))
        _RESULT_CACHE.pop(oldest, None)
    _RESULT_CACHE[result_id] = data


def _serialize_gdd(gdd: Any) -> Dict[str, Any]:
    """Serialize a GameDesignDocument into a JSON-safe dict."""
    if gdd is None:
        return {}
    concept = getattr(gdd, "concept", None)
    world = getattr(gdd, "world", None)
    characters = getattr(gdd, "characters", []) or []
    narrative = getattr(gdd, "narrative", None)
    mechanics = getattr(gdd, "mechanics", None)
    levels = getattr(gdd, "levels", None)

    return {
        "gdd_id": getattr(gdd, "gdd_id", ""),
        "quality_score": getattr(gdd, "quality_score", 0.0),
        "created_at": getattr(gdd, "created_at", 0),
        "concept": {
            "title": getattr(concept, "title", ""),
            "genre": getattr(getattr(concept, "genre", None), "value", ""),
            "theme": getattr(concept, "theme", ""),
            "visual_style": getattr(concept, "visual_style", ""),
            "core_loop": getattr(concept, "core_loop", ""),
            "player_role": getattr(concept, "player_role", ""),
            "complexity": getattr(concept, "complexity", ""),
            "estimated_playtime_min": getattr(concept, "estimated_playtime_min", 0),
            "key_features": getattr(concept, "key_features", []) or [],
            "pillars": getattr(concept, "pillars", []) or [],
            "target_mood": getattr(concept, "target_mood", []) or [],
            "innovation_angles": getattr(concept, "innovation_angles", []) or [],
            "prompt": getattr(concept, "prompt", ""),
        },
        "world": _serialize_world(world),
        "characters": [_serialize_persona(p) for p in characters],
        "narrative": _serialize_narrative(narrative),
        "mechanics": _serialize_mechanics(mechanics),
        "levels": _serialize_levels(levels),
        "asset_manifest": getattr(gdd, "asset_manifest", {}) or {},
    }


def _serialize_world(world: Any) -> Dict[str, Any]:
    if world is None:
        return {}
    return {
        "world_id": getattr(world, "world_id", ""),
        "name": getattr(world, "name", ""),
        "width": getattr(world, "width", 0),
        "height": getattr(world, "height", 0),
        "biomes": getattr(world, "biomes", []) or [],
        "structures": getattr(world, "structures", []) or [],
        "resources": getattr(world, "resources", []) or [],
        "points_of_interest": getattr(world, "points_of_interest", []) or [],
    }


def _serialize_persona(persona: Any) -> Dict[str, Any]:
    if persona is None:
        return {}
    loc = getattr(persona, "location", (0, 0))
    return {
        "persona_id": getattr(persona, "persona_id", ""),
        "name": getattr(persona, "name", ""),
        "role": getattr(persona, "role", ""),
        "personality_traits": getattr(persona, "personality_traits", []) or [],
        "backstory": getattr(persona, "backstory", ""),
        "dialogue_style": getattr(persona, "dialogue_style", ""),
        "goals": getattr(persona, "goals", []) or [],
        "fears": getattr(persona, "fears", []) or [],
        "faction": getattr(persona, "faction", ""),
        "location": [loc[0], loc[1]] if isinstance(loc, (tuple, list)) and len(loc) >= 2 else [0, 0],
    }


def _serialize_narrative(narrative: Any) -> Dict[str, Any]:
    if narrative is None:
        return {}
    return {
        "story_arcs": getattr(narrative, "story_arcs", []) or [],
        "main_quest_chain": getattr(narrative, "main_quest_chain", []) or [],
        "side_quests": getattr(narrative, "side_quests", []) or [],
        "endings": getattr(narrative, "endings", []) or [],
        "branching_points": getattr(narrative, "branching_points", []) or [],
    }


def _serialize_mechanics(mechanics: Any) -> Dict[str, Any]:
    if mechanics is None:
        return {}
    return {
        "core_mechanics": getattr(mechanics, "core_mechanics", []) or [],
        "secondary_mechanics": getattr(mechanics, "secondary_mechanics", []) or [],
        "progression_system": getattr(mechanics, "progression_system", {}) or {},
        "combat_system": getattr(mechanics, "combat_system", {}) or {},
        "economy_system": getattr(mechanics, "economy_system", {}) or {},
    }


def _serialize_levels(levels: Any) -> Dict[str, Any]:
    if levels is None:
        return {}
    return {
        "levels": getattr(levels, "levels", []) or [],
        "difficulty_curve": getattr(levels, "difficulty_curve", ""),
        "total_playtime_estimate": getattr(levels, "total_playtime_estimate", 0),
    }


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/game-synthesizer/status")
async def game_synthesizer_status():
    """Return the status of the synthesizer and game runtime."""
    try:
        status: Dict[str, Any] = {"status": "ok"}
        try:
            from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer
            synth = get_content_synthesizer()
            if not synth._initialized:
                synth.initialize()
            status["synthesizer"] = {
                "initialized": synth._initialized,
                "llm_available": synth._llm_available,
                "history_size": len(synth._synthesis_history),
            }
        except Exception as exc:
            status["synthesizer"] = {"error": str(exc)}

        try:
            from sparkai.engine.engine_game_runtime import get_game_runtime
            runtime = get_game_runtime()
            status["runtime"] = runtime.get_status()
        except Exception as exc:
            status["runtime"] = {"error": str(exc)}

        status["cache_size"] = len(_RESULT_CACHE)
        return JSONResponse({"status": "success", "data": status})
    except Exception as exc:
        logger.exception("game_synthesizer_status failed")
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.get("/game-synthesizer/genres")
async def game_synthesizer_genres():
    """Return the list of supported game genres."""
    try:
        from sparkai.agent.agent_game_content_synthesizer import GameGenre
        genres = [{"value": g.value, "name": g.value.replace("_", " ").title()} for g in GameGenre]
        return JSONResponse({"status": "success", "data": {"genres": genres}})
    except Exception as exc:
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.post("/game-synthesizer/synthesize")
async def game_synthesizer_synthesize(request: SynthesizeRequest):
    """
    Synthesize a GameDesignDocument from a natural-language prompt.

    Returns the structured GDD as JSON (no HTML game code).
    """
    try:
        from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer

        if not request.prompt or not request.prompt.strip():
            return JSONResponse(
                {"status": "error", "message": "Prompt is required"},
                status_code=400,
            )

        synth = get_content_synthesizer()
        if not synth._initialized:
            synth.initialize()

        result = synth.synthesize(
            prompt=request.prompt.strip(),
            genre_hint=request.genre_hint,
            character_count=request.character_count,
            level_count_hint=request.level_count_hint,
        )

        if not result.success or result.gdd is None:
            return JSONResponse(
                {
                    "status": "error",
                    "message": result.error or "Synthesis failed",
                    "warnings": result.warnings,
                },
                status_code=500,
            )

        gdd_json = _serialize_gdd(result.gdd)

        # Cache the result for later retrieval / HTML build
        _cache_result(result.result_id, {
            "gdd": gdd_json,
            "synthesis_result_id": result.result_id,
            "phases_completed": result.phases_completed,
            "warnings": result.warnings,
            "duration_s": result.duration_s,
        })

        return JSONResponse({
            "status": "success",
            "data": {
                "result_id": result.result_id,
                "gdd": gdd_json,
                "phases_completed": result.phases_completed,
                "phases_skipped": result.phases_skipped,
                "duration_s": result.duration_s,
                "warnings": result.warnings,
                "metadata": result.metadata,
            },
        })
    except Exception as exc:
        logger.exception("game_synthesizer_synthesize failed")
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.post("/game-synthesizer/generate")
async def game_synthesizer_generate(request: GenerateRequest):
    """
    Full pipeline: synthesize content from a prompt, then build a
    complete, playable HTML5 game.

    This is the primary "describe a game, get a game" endpoint.
    """
    try:
        from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer
        from sparkai.engine.engine_game_runtime import get_game_runtime

        if not request.prompt or not request.prompt.strip():
            return JSONResponse(
                {"status": "error", "message": "Prompt is required"},
                status_code=400,
            )

        synth = get_content_synthesizer()
        if not synth._initialized:
            synth.initialize()

        synth_result = synth.synthesize(
            prompt=request.prompt.strip(),
            genre_hint=request.genre_hint,
            character_count=request.character_count,
            level_count_hint=request.level_count_hint,
        )

        if not synth_result.success or synth_result.gdd is None:
            return JSONResponse(
                {
                    "status": "error",
                    "message": synth_result.error or "Content synthesis failed",
                    "warnings": synth_result.warnings,
                },
                status_code=500,
            )

        runtime = get_game_runtime()
        runtime_result = runtime.build_from_gdd(synth_result.gdd)

        if not runtime_result.success:
            return JSONResponse(
                {
                    "status": "error",
                    "message": runtime_result.error or "Game build failed",
                    "synthesis_result_id": synth_result.result_id,
                    "synthesis_warnings": synth_result.warnings,
                },
                status_code=500,
            )

        gdd_json = _serialize_gdd(synth_result.gdd)

        # Cache for later retrieval
        _cache_result(synth_result.result_id, {
            "gdd": gdd_json,
            "html": runtime_result.html if request.return_html else None,
            "synthesis_result_id": synth_result.result_id,
            "runtime_metadata": runtime_result.metadata,
            "phases_completed": synth_result.phases_completed,
            "warnings": synth_result.warnings,
            "duration_s": synth_result.duration_s + runtime_result.duration_s,
        })

        data: Dict[str, Any] = {
            "result_id": synth_result.result_id,
            "title": runtime_result.metadata.get("title", ""),
            "genre": runtime_result.metadata.get("genre", ""),
            "level_count": runtime_result.metadata.get("level_count", 0),
            "entity_count": runtime_result.metadata.get("entity_count", 0),
            "quality_score": synth_result.gdd.quality_score,
            "synthesis_duration_s": synth_result.duration_s,
            "build_duration_s": runtime_result.duration_s,
            "total_duration_s": round(synth_result.duration_s + runtime_result.duration_s, 3),
            "gdd": gdd_json,
            "warnings": synth_result.warnings,
            "metadata": {
                **(synth_result.metadata or {}),
                **(runtime_result.metadata or {}),
            },
        }

        if request.return_html:
            data["html"] = runtime_result.html

        return JSONResponse({"status": "success", "data": data})
    except Exception as exc:
        logger.exception("game_synthesizer_generate failed")
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.post("/game-synthesizer/build")
async def game_synthesizer_build(request: BuildRequest):
    """
    Build a playable HTML game from a previously synthesized result.

    Uses the result_id returned by /synthesize or /generate.
    """
    try:
        from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer
        from sparkai.engine.engine_game_runtime import get_game_runtime

        cached = _RESULT_CACHE.get(request.result_id)
        if cached is None:
            return JSONResponse(
                {"status": "error", "message": f"Result {request.result_id} not found in cache"},
                status_code=404,
            )

        # If HTML was already built and cached, return it directly
        if request.return_html and cached.get("html"):
            return JSONResponse({
                "status": "success",
                "data": {
                    "result_id": request.result_id,
                    "html": cached["html"],
                    "gdd": cached.get("gdd", {}),
                    "cached": True,
                },
            })

        # Otherwise we need to re-synthesize (cache only stores JSON GDD)
        # Re-run synthesis using the original prompt from the cached GDD
        gdd_json = cached.get("gdd", {})
        concept = gdd_json.get("concept", {})
        prompt = concept.get("prompt", "")

        if not prompt:
            return JSONResponse(
                {"status": "error", "message": "Cannot rebuild: original prompt not available"},
                status_code=400,
            )

        synth = get_content_synthesizer()
        if not synth._initialized:
            synth.initialize()

        synth_result = synth.synthesize(prompt)
        if not synth_result.success or synth_result.gdd is None:
            return JSONResponse(
                {"status": "error", "message": synth_result.error or "Re-synthesis failed"},
                status_code=500,
            )

        runtime = get_game_runtime()
        runtime_result = runtime.build_from_gdd(synth_result.gdd)

        if not runtime_result.success:
            return JSONResponse(
                {"status": "error", "message": runtime_result.error or "Build failed"},
                status_code=500,
            )

        # Update cache with fresh HTML
        cached["html"] = runtime_result.html if request.return_html else None
        cached["runtime_metadata"] = runtime_result.metadata

        data: Dict[str, Any] = {
            "result_id": request.result_id,
            "title": runtime_result.metadata.get("title", ""),
            "genre": runtime_result.metadata.get("genre", ""),
            "level_count": runtime_result.metadata.get("level_count", 0),
            "gdd": _serialize_gdd(synth_result.gdd),
            "cached": False,
        }
        if request.return_html:
            data["html"] = runtime_result.html

        return JSONResponse({"status": "success", "data": data})
    except Exception as exc:
        logger.exception("game_synthesizer_build failed")
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.get("/game-synthesizer/result/{result_id}")
async def game_synthesizer_get_result(result_id: str):
    """Retrieve a previously cached synthesis result by ID."""
    try:
        cached = _RESULT_CACHE.get(result_id)
        if cached is None:
            return JSONResponse(
                {"status": "error", "message": f"Result {result_id} not found"},
                status_code=404,
            )
        return JSONResponse({
            "status": "success",
            "data": {
                "result_id": result_id,
                "gdd": cached.get("gdd", {}),
                "has_html": bool(cached.get("html")),
                "synthesis_result_id": cached.get("synthesis_result_id"),
                "phases_completed": cached.get("phases_completed", []),
                "warnings": cached.get("warnings", []),
                "duration_s": cached.get("duration_s", 0),
                "runtime_metadata": cached.get("runtime_metadata", {}),
            },
        })
    except Exception as exc:
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.get("/game-synthesizer/history")
async def game_synthesizer_history():
    """Return a summary of recent synthesis results."""
    try:
        from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer
        synth = get_content_synthesizer()
        history = list(synth._synthesis_history)
        return JSONResponse({
            "status": "success",
            "data": {
                "history": history,
                "count": len(history),
            },
        })
    except Exception as exc:
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )
