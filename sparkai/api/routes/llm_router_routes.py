"""
SparkLabs API - LLM Router Routes

API endpoints for the LLM Router module. Exposes router status,
provider and model catalogs, request routing, routing strategies,
statistics, and cache management.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sparkai.agent.agent_llm_router import (
    LLMRouter,
    ModelRequest,
    ModelType,
    RoutingStrategy,
    TaskType,
    get_llm_router,
)


router = APIRouter()

# Lookup tables mapping string values to their enum members.
_MODEL_TYPE_MAP: Dict[str, ModelType] = {mt.value: mt for mt in ModelType}
_TASK_TYPE_MAP: Dict[str, TaskType] = {tt.value: tt for tt in TaskType}


class RouteRequestModel(BaseModel):
    """Request body for routing a task to the best available model."""

    task_type: str = "dialogue"
    prompt: str = ""
    system_prompt: str = ""
    model_id: Optional[str] = None
    provider_id: Optional[str] = None
    max_cost: Optional[float] = None
    max_latency_ms: Optional[float] = None
    prefer_streaming: bool = False
    use_cache: bool = True


class ExecuteRequestModel(BaseModel):
    """Request body for executing a model request end-to-end."""

    task_type: str = "dialogue"
    prompt: str = ""
    system_prompt: str = ""
    model_id: Optional[str] = None
    provider_id: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    images: Optional[List[str]] = None
    use_cache: bool = True


class GenerateImageRequest(BaseModel):
    """Request body for image generation."""

    prompt: str
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
    width: int = 1024
    height: int = 1024
    n: int = 1


class GenerateAudioRequest(BaseModel):
    """Request body for text-to-speech / audio generation."""

    text: str
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
    voice: str = "alloy"


class GenerateVideoRequest(BaseModel):
    """Request body for video generation."""

    prompt: str
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
    duration: int = 5


class Generate3DRequest(BaseModel):
    """Request body for 3D model generation."""

    prompt: str
    provider_id: Optional[str] = None
    model_id: Optional[str] = None


class RegisterProviderRequest(BaseModel):
    """Request body for registering or updating a provider configuration."""

    name: str
    provider: str = ""
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    cost_per_1k: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    quality_score: Optional[float] = None


@router.get("/status")
async def get_router_status():
    """Return the current status and health of the LLM router."""
    try:
        llm_router = get_llm_router()
        providers = llm_router.list_providers()
        models = llm_router.list_models()
        return {
            "status": "success",
            "data": {
                "router_active": True,
                "simulation_mode": llm_router.get_simulation_mode(),
                "routing_strategy": llm_router.get_routing_strategy().value,
                "provider_count": len(providers),
                "model_count": len(models),
                "cache_stats": llm_router.get_cache_stats(),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/providers")
async def list_providers():
    """List all registered model providers."""
    try:
        llm_router = get_llm_router()
        providers = llm_router.list_providers()
        return {
            "status": "success",
            "data": {
                "providers": providers,
                "count": len(providers),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/models")
async def list_models():
    """List all available models with their types."""
    try:
        llm_router = get_llm_router()
        models = llm_router.list_models()
        return {
            "status": "success",
            "data": {
                "models": models,
                "count": len(models),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/models/{model_type}")
async def list_models_by_type(model_type: str):
    """List models filtered by model type.

    Valid types: text, vision, image_gen, video_gen, audio_gen,
    tts, stt, embedding, code, reasoning, multimodal, 3d_gen, animation.
    """
    try:
        resolved = _MODEL_TYPE_MAP.get(model_type)
        if resolved is None:
            valid_types = sorted(_MODEL_TYPE_MAP.keys())
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Unknown model type: {model_type}",
                    "valid_types": valid_types,
                },
            )
        llm_router = get_llm_router()
        models = llm_router.search_models(model_type=resolved, limit=500)
        return {
            "status": "success",
            "data": {
                "model_type": model_type,
                "models": models,
                "count": len(models),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/route")
async def route_request(request: RouteRequestModel):
    """Route a request to the best model for the given task."""
    try:
        resolved_task = _TASK_TYPE_MAP.get(request.task_type)
        if resolved_task is None:
            valid_types = sorted(_TASK_TYPE_MAP.keys())
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Unknown task type: {request.task_type}",
                    "valid_types": valid_types,
                },
            )
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=resolved_task,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            model_id=request.model_id,
            provider_id=request.provider_id,
            max_cost=request.max_cost,
            max_latency_ms=request.max_latency_ms,
            prefer_streaming=request.prefer_streaming,
            use_cache=request.use_cache,
        )
        provider_id, model_id = llm_router.route_request(model_request)
        if not provider_id and not model_id:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "No available provider or model for the requested task",
                },
            )
        return {
            "status": "success",
            "data": {
                "provider_id": provider_id,
                "model_id": model_id,
                "task_type": request.task_type,
                "routing_strategy": llm_router.get_routing_strategy().value,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/strategies")
async def list_routing_strategies():
    """List all available routing strategies."""
    try:
        strategies: List[Dict[str, Any]] = [
            {"value": s.value, "name": s.name} for s in RoutingStrategy
        ]
        llm_router = get_llm_router()
        active = llm_router.get_routing_strategy().value
        return {
            "status": "success",
            "data": {
                "strategies": strategies,
                "active": active,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/stats")
async def get_router_stats():
    """Return router statistics including provider and model counts and cache stats."""
    try:
        llm_router = get_llm_router()
        providers = llm_router.list_providers()
        models = llm_router.list_models()
        return {
            "status": "success",
            "data": {
                "provider_count": len(providers),
                "model_count": len(models),
                "routing_strategy": llm_router.get_routing_strategy().value,
                "simulation_mode": llm_router.get_simulation_mode(),
                "cache_stats": llm_router.get_cache_stats(),
                "usage_stats": llm_router.get_usage_stats(),
                "cost_report": llm_router.get_cost_report(),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/cache/clear")
async def clear_cache():
    """Clear the response cache and return the number of evicted entries."""
    try:
        llm_router = get_llm_router()
        evicted = llm_router.clear_cache()
        return {
            "status": "success",
            "data": {
                "evicted_entries": evicted,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/register")
async def register_provider(request: RegisterProviderRequest):
    """Register or update a provider configuration with API key and base URL."""
    try:
        llm_router = get_llm_router()
        provider_id = request.provider or request.name
        if request.api_key:
            llm_router.set_api_key(
                provider_id=provider_id,
                api_key=request.api_key,
            )
        if request.base_url:
            llm_router.set_provider_base_url(
                provider_id=provider_id,
                base_url=request.base_url,
            )
        return {
            "status": "success",
            "data": {
                "provider": provider_id,
                "configured": True,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/execute")
async def execute_request(request: ExecuteRequestModel):
    """Execute a model request end-to-end and return the response."""
    try:
        resolved_task = _TASK_TYPE_MAP.get(request.task_type)
        if resolved_task is None:
            valid_types = sorted(_TASK_TYPE_MAP.keys())
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Unknown task type: {request.task_type}",
                    "valid_types": valid_types,
                },
            )
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=resolved_task,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            model_id=request.model_id,
            provider_id=request.provider_id,
            use_cache=request.use_cache,
        )
        response = llm_router.execute_request(model_request)
        return {
            "status": "success",
            "data": response.to_dict(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/generate/image")
async def generate_image(request: GenerateImageRequest):
    """Generate an image from a text prompt using the best available image model."""
    try:
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.ASSET_IMAGE,
            prompt=request.prompt,
            provider_id=request.provider_id,
            model_id=request.model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "status": "success",
            "data": {
                "images": response.content_urls,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/generate/audio")
async def generate_audio(request: GenerateAudioRequest):
    """Generate audio from text using text-to-speech or audio generation models."""
    try:
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.VOICE_ACTING,
            prompt=request.text,
            provider_id=request.provider_id,
            model_id=request.model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "status": "success",
            "data": {
                "audio_urls": response.content_urls,
                "content": response.content,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/generate/video")
async def generate_video(request: GenerateVideoRequest):
    """Generate video from a text prompt using the best available video model."""
    try:
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.ASSET_VIDEO,
            prompt=request.prompt,
            provider_id=request.provider_id,
            model_id=request.model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "status": "success",
            "data": {
                "video_urls": response.content_urls,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/generate/3d")
async def generate_3d(request: Generate3DRequest):
    """Generate a 3D model from a text prompt using the best available 3D model."""
    try:
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.ASSET_3D,
            prompt=request.prompt,
            provider_id=request.provider_id,
            model_id=request.model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "status": "success",
            "data": {
                "model_urls": response.content_urls,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )
