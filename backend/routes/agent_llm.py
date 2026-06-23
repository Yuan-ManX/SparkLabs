"""
SparkLabs Backend - Agent LLM Pipeline Routes

API endpoints for LLM-powered text generation, reasoning,
provider management, prompt templates, response parsing,
and usage statistics.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for LLM usage tracking
_llm_requests: List[Dict[str, Any]] = []
_total_tokens: int = 0
_total_errors: int = 0

# Mock LLM providers
_providers: List[Dict[str, Any]] = [
    {"id": "openai", "name": "OpenAI", "models": ["gpt-4", "gpt-3.5-turbo"], "status": "available"},
    {"id": "anthropic", "name": "Anthropic", "models": ["claude-3-opus", "claude-3-sonnet"], "status": "available"},
    {"id": "local", "name": "Local LLM", "models": ["llama-3", "mistral"], "status": "available"},
    {"id": "default", "name": "Default Provider", "models": ["default-model"], "status": "available"},
]

# Mock prompt templates
_template_categories: List[str] = ["SYSTEM", "NARRATIVE", "DIALOGUE", "REASONING", "CREATIVE"]
_templates: List[Dict[str, Any]] = [
    {"id": "system-prompt", "name": "System Prompt", "category": "SYSTEM", "description": "Default system behavior prompt"},
    {"id": "narrative-gen", "name": "Narrative Generation", "category": "NARRATIVE", "description": "Generate story narratives"},
    {"id": "dialogue-tree", "name": "Dialogue Tree", "category": "DIALOGUE", "description": "Generate branching dialogue"},
    {"id": "chain-of-thought", "name": "Chain of Thought", "category": "REASONING", "description": "Step-by-step reasoning prompt"},
    {"id": "creative-writing", "name": "Creative Writing", "category": "CREATIVE", "description": "Creative content generation"},
]


class GenerateRequest(BaseModel):
    prompt: str
    template_category: str = "SYSTEM"
    variables: Dict[str, Any] = {}
    provider: str = "default"


class ReasonRequest(BaseModel):
    problem: str
    strategy: str = "CHAIN_OF_THOUGHT"
    max_steps: int = 5


class ParseRequest(BaseModel):
    response_text: str
    expected_format: str = "json"


@router.post("/llm/generate")
async def generate_text(request: GenerateRequest):
    try:
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        tokens_used = len(request.prompt.split()) * 2 + 50
        latency_ms = 150.0 + (len(request.prompt) * 0.5)

        template = next(
            (t for t in _templates if t.get("category") == request.template_category),
            _templates[0],
        )

        response_text = (
            f"[{template.get('name', 'Response')}] Generated response for: "
            f"{request.prompt[:100]}..."
        )

        _llm_requests.append({
            "id": request_id,
            "type": "generate",
            "provider": request.provider,
            "template_category": request.template_category,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "timestamp": timestamp,
        })

        global _total_tokens
        _total_tokens += tokens_used

        return {
            "status": "success",
            "data": {
                "response": response_text,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
            },
        }
    except Exception as e:
        global _total_errors
        _total_errors += 1
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/llm/reason")
async def chain_of_thought_reasoning(request: ReasonRequest):
    try:
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        reasoning_steps = []
        for step in range(1, request.max_steps + 1):
            reasoning_steps.append({
                "step": step,
                "thought": f"Analyzing aspect {step} of the problem: {request.problem[:50]}...",
                "insight": f"Key insight from step {step}",
                "confidence": min(0.5 + (step * 0.1), 1.0),
            })

        conclusion = (
            f"After {request.max_steps} steps of {request.strategy} reasoning, "
            f"the analysis of '{request.problem[:50]}...' is complete."
        )
        confidence = 0.85

        tokens_used = len(request.problem.split()) * request.max_steps * 3
        latency_ms = 200.0 + (request.max_steps * 100.0)

        _llm_requests.append({
            "id": request_id,
            "type": "reason",
            "strategy": request.strategy,
            "max_steps": request.max_steps,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "timestamp": timestamp,
        })

        global _total_tokens
        _total_tokens += tokens_used

        return {
            "status": "success",
            "data": {
                "conclusion": conclusion,
                "reasoning_steps": reasoning_steps,
                "confidence": confidence,
            },
        }
    except Exception as e:
        global _total_errors
        _total_errors += 1
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/llm/providers")
async def list_providers():
    try:
        return {
            "status": "success",
            "data": {
                "providers": _providers,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/llm/templates")
async def list_templates():
    try:
        return {
            "status": "success",
            "data": {
                "templates": _templates,
                "categories": _template_categories,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/llm/parse")
async def parse_llm_response(request: ParseRequest):
    try:
        import json
        is_valid = False
        parsed: Dict[str, Any] = {}

        if request.expected_format == "json":
            try:
                parsed = json.loads(request.response_text)
                is_valid = True
            except json.JSONDecodeError:
                parsed = {"raw_text": request.response_text, "error": "Invalid JSON"}
                is_valid = False
        else:
            parsed = {
                "format": request.expected_format,
                "content": request.response_text,
                "length": len(request.response_text),
            }
            is_valid = True

        return {
            "status": "success",
            "data": {
                "parsed": parsed,
                "is_valid": is_valid,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/llm/stats")
async def get_llm_stats():
    try:
        total_requests = len(_llm_requests)
        avg_latency_ms = 0.0
        if _llm_requests:
            avg_latency_ms = sum(
                r.get("latency_ms", 0) for r in _llm_requests
            ) / total_requests

        error_rate = 0.0
        if total_requests > 0:
            error_rate = _total_errors / (total_requests + _total_errors)

        return {
            "status": "success",
            "data": {
                "total_requests": total_requests,
                "total_tokens": _total_tokens,
                "avg_latency_ms": round(avg_latency_ms, 2),
                "error_rate": round(error_rate, 4),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )