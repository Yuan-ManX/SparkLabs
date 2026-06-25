"""
SparkAI Strategic Synthesis & Game Vision API Routes.

Provides REST endpoints for strategic synthesis reasoning,
game vision analysis, and design intelligence operations.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import time

router = APIRouter()


# --- Request Models ---

class SynthesizeRequest(BaseModel):
    """Request for strategic synthesis analysis."""
    objective: str
    domain: str = "game_design"
    constraints: Optional[List[str]] = None
    strategy: str = "adaptive_ensemble"


class CreateVisionRequest(BaseModel):
    """Request for game vision creation."""
    game_concept: str
    genre: str
    target_audience: Optional[List[str]] = None
    constraints: Optional[List[str]] = None


class GameplayAnalysisRequest(BaseModel):
    """Request for gameplay analysis."""
    concept: str
    mechanics: Optional[List[str]] = None


# --- Synthesis Endpoints ---

@router.post("/strategic/synthesize")
async def strategic_synthesize(request: SynthesizeRequest):
    """Execute strategic synthesis reasoning."""
    try:
        from sparkai.agent.agent_strategic_synthesis import (
            StrategicSynthesisEngine, SynthesisDomain, ReasoningStrategy,
        )

        engine = StrategicSynthesisEngine.get_instance()
        if not engine._initialized:
            engine.initialize()

        try:
            domain = SynthesisDomain(request.domain)
        except ValueError:
            domain = SynthesisDomain.GAME_DESIGN

        try:
            strategy = ReasoningStrategy(request.strategy)
        except ValueError:
            strategy = ReasoningStrategy.ADAPTIVE_ENSEMBLE

        context = engine.create_session(
            objective=request.objective,
            domain=domain,
            constraints=request.constraints,
        )

        result = engine.synthesize(context, strategy=strategy)

        return {
            "status": "success",
            "data": result.to_dict(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/strategic/stats")
async def strategic_stats():
    """Get strategic synthesis engine statistics."""
    try:
        from sparkai.agent.agent_strategic_synthesis import (
            StrategicSynthesisEngine,
        )

        engine = StrategicSynthesisEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_statistics(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/strategic/history")
async def strategic_history(limit: int = Query(20, ge=1, le=100)):
    """Get strategic synthesis history."""
    try:
        from sparkai.agent.agent_strategic_synthesis import (
            StrategicSynthesisEngine,
        )

        engine = StrategicSynthesisEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_history(limit=limit),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/strategic/initialize")
async def strategic_initialize():
    """Initialize the strategic synthesis engine."""
    try:
        from sparkai.agent.agent_strategic_synthesis import (
            StrategicSynthesisEngine,
        )

        engine = StrategicSynthesisEngine.get_instance()
        engine.initialize()
        return {
            "status": "success",
            "data": {
                "initialized": engine._initialized,
                "message": "Strategic synthesis engine initialized",
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# --- Game Vision Endpoints ---

@router.post("/vision/create")
async def create_game_vision(request: CreateVisionRequest):
    """Create a comprehensive game vision profile."""
    try:
        from sparkai.agent.agent_game_vision import GameVisionEngine

        engine = GameVisionEngine.get_instance()
        if not engine._initialized:
            engine.initialize()

        vision = engine.create_vision(
            game_concept=request.game_concept,
            genre=request.genre,
            target_audience=request.target_audience,
            constraints=request.constraints,
        )

        return {
            "status": "success",
            "data": vision.to_dict(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/vision/analyze-gameplay")
async def analyze_gameplay(request: GameplayAnalysisRequest):
    """Analyze gameplay mechanics and systems."""
    try:
        from sparkai.agent.agent_game_vision import GameVisionEngine

        engine = GameVisionEngine.get_instance()
        if not engine._initialized:
            engine.initialize()

        analysis = engine.analyze_gameplay(
            concept=request.concept,
            mechanics=request.mechanics,
        )

        return {
            "status": "success",
            "data": analysis.to_dict(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/vision/stats")
async def vision_stats():
    """Get game vision engine statistics."""
    try:
        from sparkai.agent.agent_game_vision import GameVisionEngine

        engine = GameVisionEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_statistics(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/vision/list")
async def vision_list(limit: int = Query(20, ge=1, le=100)):
    """List game vision profiles."""
    try:
        from sparkai.agent.agent_game_vision import GameVisionEngine

        engine = GameVisionEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_visions(limit=limit),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/vision/{vision_id}")
async def get_vision(vision_id: str):
    """Get a specific game vision profile."""
    try:
        from sparkai.agent.agent_game_vision import GameVisionEngine

        engine = GameVisionEngine.get_instance()
        vision = engine.get_vision(vision_id)
        if not vision:
            raise HTTPException(status_code=404, detail="Vision not found")
        return {
            "status": "success",
            "data": vision.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/vision/initialize")
async def vision_initialize():
    """Initialize the game vision engine."""
    try:
        from sparkai.agent.agent_game_vision import GameVisionEngine

        engine = GameVisionEngine.get_instance()
        engine.initialize()
        return {
            "status": "success",
            "data": {
                "initialized": engine._initialized,
                "message": "Game vision engine initialized",
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )