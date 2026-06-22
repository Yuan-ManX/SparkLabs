"""
SparkLabs Backend - Terrain Generation Routes

API endpoints for terrain generation including
chunk generation, erosion simulation, and biome mapping.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for terrain data
_terrain_chunks: Dict[str, Dict[str, Any]] = {}
_biome_map: Dict[str, Dict[str, Any]] = {
    "tundra": {"temperature_range": [-30, 0], "precipitation_range": [0, 0.3], "color": "#c8d6e5"},
    "taiga": {"temperature_range": [-10, 10], "precipitation_range": [0.2, 0.5], "color": "#5b8c5a"},
    "temperate_forest": {"temperature_range": [5, 20], "precipitation_range": [0.4, 0.8], "color": "#2d8c2d"},
    "grassland": {"temperature_range": [10, 25], "precipitation_range": [0.2, 0.5], "color": "#c5d93d"},
    "desert": {"temperature_range": [20, 45], "precipitation_range": [0, 0.15], "color": "#e8c47c"},
    "tropical_rainforest": {"temperature_range": [20, 35], "precipitation_range": [0.7, 1.0], "color": "#1a6b1a"},
    "savanna": {"temperature_range": [18, 30], "precipitation_range": [0.2, 0.6], "color": "#d4a853"},
    "mediterranean": {"temperature_range": [10, 25], "precipitation_range": [0.3, 0.6], "color": "#a8c256"},
}


class TerrainGenerateRequest(BaseModel):
    chunk_x: int = 0
    chunk_y: int = 0
    size: int = 256
    seed: Optional[int] = None
    biome: str = "temperate_forest"
    height_multiplier: float = 1.0
    noise_octaves: int = 4
    metadata: Optional[Dict[str, Any]] = None


class TerrainErodeRequest(BaseModel):
    chunk_id: str
    iterations: int = 100
    erosion_rate: float = 0.01
    deposition_rate: float = 0.005
    seed: Optional[int] = None


@router.post("/terrain/generate")
async def generate_terrain(request: TerrainGenerateRequest):
    try:
        chunk_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        chunk = {
            "id": chunk_id,
            "chunk_x": request.chunk_x,
            "chunk_y": request.chunk_y,
            "size": request.size,
            "seed": request.seed or 42,
            "biome": request.biome,
            "height_multiplier": request.height_multiplier,
            "noise_octaves": request.noise_octaves,
            "metadata": request.metadata or {},
            "vertex_count": request.size * request.size,
            "height_range": [0.0, request.height_multiplier * 100.0],
            "erosion_applied": False,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        _terrain_chunks[chunk_id] = chunk

        return {"status": "success", "data": chunk}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/terrain/chunk/{chunk_id}")
async def get_terrain_chunk(chunk_id: str):
    try:
        chunk = _terrain_chunks.get(chunk_id)
        if chunk:
            return {"status": "success", "data": chunk}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Terrain chunk not found"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/terrain/erode")
async def erode_terrain(request: TerrainErodeRequest):
    try:
        chunk = _terrain_chunks.get(request.chunk_id)
        if not chunk:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Terrain chunk not found"},
            )

        timestamp = datetime.utcnow().isoformat()

        erosion_result = {
            "chunk_id": request.chunk_id,
            "iterations": request.iterations,
            "erosion_rate": request.erosion_rate,
            "deposition_rate": request.deposition_rate,
            "height_range_before": chunk.get("height_range", [0, 0]),
            "height_range_after": [
                max(0, chunk.get("height_range", [0, 0])[0] * 0.95),
                chunk.get("height_range", [0, 0])[1] * 0.85,
            ],
            "sediment_transported": request.iterations
            * request.erosion_rate
            * 100,
            "applied_at": timestamp,
        }

        chunk["erosion_applied"] = True
        chunk["height_range"] = erosion_result["height_range_after"]
        chunk["updated_at"] = timestamp

        return {"status": "success", "data": erosion_result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/terrain/biome-map")
async def get_biome_map():
    try:
        return {
            "status": "success",
            "data": {
                "biomes": _biome_map,
                "total_biomes": len(_biome_map),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )