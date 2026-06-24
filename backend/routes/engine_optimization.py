"""
SparkAI Engine Optimization API Routes.

Provides REST endpoints for adaptive rendering optimization,
physics performance tuning, and engine configuration management.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

router = APIRouter()


# --- Request Models ---

class UpdateMetricsRequest(BaseModel):
    """Request to update rendering performance metrics."""
    current_fps: float = 60.0
    target_fps: float = 60.0
    frame_time_ms: float = 16.67
    gpu_utilization: float = 0.5
    cpu_utilization: float = 0.3
    memory_usage_mb: float = 256.0
    draw_calls: int = 100
    triangle_count: int = 50000
    texture_memory_mb: float = 128.0
    shader_complexity: Union[float, str] = 0.5
    screen_fill_percentage: float = 0.7


class AdaptiveInitRequest(BaseModel):
    """Request to initialize adaptive rendering."""
    target_fps: float = 60.0
    strategy: str = "balanced"


class OverrideFeatureRequest(BaseModel):
    """Request to override a render feature."""
    feature: str
    enabled: bool


class PhysicsProfileRequest(BaseModel):
    """Request to record a physics performance profile."""
    body_count: int = 0
    active_body_count: int = 0
    sleeping_body_count: int = 0
    collision_pair_count: int = 0
    contact_count: int = 0
    constraint_count: int = 0
    island_count: int = 0
    broad_phase_time_ms: float = 0.0
    narrow_phase_time_ms: float = 0.0
    solver_time_ms: float = 0.0
    integration_time_ms: float = 0.0
    total_physics_time_ms: float = 0.0


class PhysicsConfigUpdateRequest(BaseModel):
    """Request to update physics configuration."""
    updates: Dict[str, Any]


class ApplyRecommendationRequest(BaseModel):
    """Request to apply a physics optimization recommendation."""
    recommendation_id: str


# --- Adaptive Rendering Endpoints ---

@router.get("/adaptive-rendering/stats")
async def adaptive_rendering_stats():
    """Get adaptive rendering engine statistics."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_statistics(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/adaptive-rendering/config")
async def adaptive_rendering_config():
    """Get current adaptive rendering configuration."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_current_config(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/adaptive-rendering/initialize")
async def adaptive_rendering_initialize(request: AdaptiveInitRequest):
    """Initialize the adaptive rendering engine."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine, AdaptationStrategy,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        try:
            strategy = AdaptationStrategy(request.strategy)
        except ValueError:
            strategy = AdaptationStrategy.BALANCED

        engine.initialize(target_fps=request.target_fps, strategy=strategy)
        return {
            "status": "success",
            "data": engine.get_current_config(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/adaptive-rendering/metrics")
async def update_rendering_metrics(request: UpdateMetricsRequest):
    """Update rendering performance metrics."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine, PerformanceMetrics,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        if not engine._initialized:
            engine.initialize()

        # Convert shader_complexity from string to float if needed
        sc = request.shader_complexity
        if isinstance(sc, str):
            sc_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "ultra": 1.0}
            sc = sc_map.get(sc.lower(), 0.5)

        metrics = PerformanceMetrics(
            current_fps=request.current_fps,
            target_fps=request.target_fps,
            frame_time_ms=request.frame_time_ms,
            gpu_utilization=request.gpu_utilization,
            cpu_utilization=request.cpu_utilization,
            memory_usage_mb=request.memory_usage_mb,
            draw_calls=request.draw_calls,
            triangle_count=request.triangle_count,
            texture_memory_mb=request.texture_memory_mb,
            shader_complexity=float(sc),
            screen_fill_percentage=request.screen_fill_percentage,
        )

        engine.update_metrics(metrics)
        return {
            "status": "success",
            "data": engine.get_current_config(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/adaptive-rendering/enable")
async def adaptive_rendering_enable():
    """Enable adaptive rendering."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        engine.set_enabled(True)
        return {"status": "success", "data": {"enabled": True}}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/adaptive-rendering/disable")
async def adaptive_rendering_disable():
    """Disable adaptive rendering."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        engine.set_enabled(False)
        return {"status": "success", "data": {"enabled": False}}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/adaptive-rendering/feature-override")
async def override_render_feature(request: OverrideFeatureRequest):
    """Override a specific render feature."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine, RenderFeature,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        try:
            feature = RenderFeature(request.feature)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid feature: {request.feature}")

        engine._quality_manager.override_feature(feature, request.enabled)
        return {
            "status": "success",
            "data": engine.get_current_config(),
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/adaptive-rendering/presets")
async def adaptive_rendering_presets():
    """Get all available quality presets."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_all_presets(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/adaptive-rendering/history")
async def adaptive_rendering_history(limit: int = Query(50, ge=1, le=200)):
    """Get adaptation event history."""
    try:
        from sparkai.engine.engine_adaptive_rendering import (
            AdaptiveRenderingEngine,
        )

        engine = AdaptiveRenderingEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_adaptation_history(limit=limit),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# --- Physics Optimizer Endpoints ---

@router.get("/physics-optimizer/stats")
async def physics_optimizer_stats():
    """Get physics optimizer statistics."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_statistics(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/physics-optimizer/config")
async def physics_optimizer_config():
    """Get current physics configuration."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_configuration(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/physics-optimizer/initialize")
async def physics_optimizer_initialize():
    """Initialize the physics optimizer engine."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        engine.initialize()
        return {
            "status": "success",
            "data": {
                "initialized": engine._initialized,
                "message": "Physics optimizer engine initialized",
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/physics-optimizer/profile")
async def record_physics_profile(request: PhysicsProfileRequest):
    """Record a physics performance profile."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine, PhysicsProfile,
        )

        import uuid

        engine = PhysicsOptimizerEngine.get_instance()
        if not engine._initialized:
            engine.initialize()

        profile = PhysicsProfile(
            profile_id=f"profile_{uuid.uuid4().hex[:8]}",
            body_count=request.body_count,
            active_body_count=request.active_body_count,
            sleeping_body_count=request.sleeping_body_count,
            collision_pair_count=request.collision_pair_count,
            contact_count=request.contact_count,
            constraint_count=request.constraint_count,
            island_count=request.island_count,
            broad_phase_time_ms=request.broad_phase_time_ms,
            narrow_phase_time_ms=request.narrow_phase_time_ms,
            solver_time_ms=request.solver_time_ms,
            integration_time_ms=request.integration_time_ms,
            total_physics_time_ms=request.total_physics_time_ms,
        )

        engine.record_profile(profile)
        return {
            "status": "success",
            "data": profile.to_dict(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/physics-optimizer/analyze")
async def analyze_physics():
    """Analyze physics performance and generate recommendations."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        recommendations = engine.analyze()
        return {
            "status": "success",
            "data": {
                "recommendations": [r.to_dict() for r in recommendations],
                "count": len(recommendations),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/physics-optimizer/apply-recommendation")
async def apply_physics_recommendation(request: ApplyRecommendationRequest):
    """Apply a physics optimization recommendation."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        success = engine.apply_recommendation(request.recommendation_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Recommendation not found or not auto-applicable",
            )
        return {
            "status": "success",
            "data": {
                "applied": True,
                "recommendation_id": request.recommendation_id,
                "config": engine.get_configuration(),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.put("/physics-optimizer/config")
async def update_physics_config(request: PhysicsConfigUpdateRequest):
    """Update physics configuration parameters."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        if not engine._initialized:
            engine.initialize()

        config = engine.update_configuration(request.updates)
        return {
            "status": "success",
            "data": config,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/physics-optimizer/profiles")
async def physics_profiles(limit: int = Query(50, ge=1, le=200)):
    """Get physics performance profiles."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_profiles(limit=limit),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/physics-optimizer/recommendations")
async def physics_recommendations():
    """Get current physics optimization recommendations."""
    try:
        from sparkai.engine.engine_physics_optimizer import (
            PhysicsOptimizerEngine,
        )

        engine = PhysicsOptimizerEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_recommendations(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )