"""
SparkLabs Backend - FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sparkai.config import SparkAIConfig
from backend.routes import (
    engine, agent, scene, workflow, narrative, npc,
    agent_memory, agent_goals, engine_level, engine_weather,
    engine_terrain, agent_social, agent_llm, agent_game_creation, agent_swarm,
    engine_behavior, agent_cognitive, agent_creator, agent_orchestration,
    agent_strategic, engine_optimization, agent_learning, agent_ai_native,
    agent_core_systems, agent_engine_unified, agent_orchestrator,
    agent_game_forge, agent_engine_unified_v2, agent_ai_native_orchestrator,
    agent_engine_integration, agent_game_synthesizer, agent_game_director,
)
from backend.websocket import router as ws_router
from sparkai.api.routes import llm_router_routes

config = SparkAIConfig()

app = FastAPI(
    title="SparkLabs API",
    description="SparkLabs AI-Native Game Engine API",
    version="17.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engine.router, prefix="/api/engine", tags=["Engine"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(scene.router, prefix="/api/scene", tags=["Scene"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(narrative.router, prefix="/api/narrative", tags=["Narrative"])
app.include_router(npc.router, prefix="/api/npc", tags=["NPC"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
app.include_router(agent_memory.router, prefix="/api/agent", tags=["Agent Memory"])
app.include_router(agent_goals.router, prefix="/api/agent", tags=["Agent Goals"])
app.include_router(agent_social.router, prefix="/api/agent", tags=["Agent Social"])
app.include_router(engine_level.router, prefix="/api/engine", tags=["Engine Level"])
app.include_router(engine_weather.router, prefix="/api/engine", tags=["Engine Weather"])
app.include_router(engine_terrain.router, prefix="/api/engine", tags=["Engine Terrain"])
app.include_router(agent_llm.router, prefix="/api/agent", tags=["Agent LLM"])
app.include_router(agent_game_creation.router, prefix="/api/agent", tags=["Agent Game Creation"])
app.include_router(agent_swarm.router, prefix="/api/agent", tags=["Agent Swarm"])
app.include_router(agent_cognitive.router, prefix="/api/agent", tags=["Agent Cognitive"])
app.include_router(agent_creator.router, prefix="/api/agent", tags=["Agent Creator"])
app.include_router(engine_behavior.router, prefix="/api/engine", tags=["Engine Behavior"])
app.include_router(agent_orchestration.router, prefix="/api/agent", tags=["Agent Orchestration"])
app.include_router(agent_strategic.router, prefix="/api/agent", tags=["Agent Strategic"])
app.include_router(engine_optimization.router, prefix="/api/engine", tags=["Engine Optimization"])
app.include_router(agent_learning.router, prefix="/api/agent", tags=["Agent Learning"])
app.include_router(agent_ai_native.router, prefix="/api/agent", tags=["Agent AI-Native"])
app.include_router(agent_core_systems.router, prefix="/api/agent", tags=["Agent Core Systems"])
app.include_router(agent_engine_unified.router, prefix="/api/agent", tags=["Agent & Engine Unified Systems"])
app.include_router(agent_orchestrator.router, prefix="/api/agent", tags=["Agent Orchestrator"])
app.include_router(agent_game_forge.router, prefix="/api/agent", tags=["Agent Game Forge"])
app.include_router(agent_engine_unified_v2.router, prefix="/api", tags=["Unified Agent & Engine Core v2"])
app.include_router(agent_ai_native_orchestrator.router, prefix="/api/agent", tags=["AI-Native Game Orchestrator"])
app.include_router(agent_engine_integration.router, prefix="/api", tags=["Agent & Engine Integration"])
app.include_router(agent_game_synthesizer.router, prefix="/api/agent", tags=["Game Synthesizer"])
app.include_router(agent_game_director.router, prefix="/api/agent", tags=["Game Director"])
app.include_router(llm_router_routes.router, prefix="/api/llm-router", tags=["LLM Router"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "17.0.0", "engine": "SparkLabs"}


@app.get("/api/status")
async def get_status():
    from sparkai.engine.engine import SparkEngine
    engine_instance = SparkEngine.get_instance()
    return {
        "engine": engine_instance.get_status(),
        "version": "17.0.0",
    }
