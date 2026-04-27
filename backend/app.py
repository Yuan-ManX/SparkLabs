"""
SparkLabs Backend - FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sparkai.config import SparkAIConfig
from backend.routes import engine, agent, scene, workflow, narrative, npc
from backend.websocket import router as ws_router

config = SparkAIConfig()

app = FastAPI(
    title="SparkLabs API",
    description="SparkLabs AI-Native Game Engine API",
    version="2.0.0",
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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0", "engine": "SparkLabs"}


@app.get("/api/status")
async def get_status():
    from sparkai.engine.engine import SparkEngine
    engine_instance = SparkEngine.get_instance()
    return {
        "engine": engine_instance.get_status(),
        "version": "2.0.0",
    }
