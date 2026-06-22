"""
SparkLabs Backend - Level Streaming Routes

API endpoints for level streaming including
cell management, level loading/unloading,
and streaming status monitoring.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for streaming cells
_cells: Dict[str, Dict[str, Any]] = {}
_streaming_state: Dict[str, Any] = {
    "active": False,
    "loaded_cells": [],
    "pending_cells": [],
    "stream_budget": 100,
}


class CellCreateRequest(BaseModel):
    name: str = "Cell"
    bounds: List[float] = [0, 0, 0, 100, 100, 100]
    priority: int = 0
    metadata: Optional[Dict[str, Any]] = None


class CellLoadRequest(BaseModel):
    cell_id: str
    priority: int = 0


class CellUnloadRequest(BaseModel):
    cell_id: str
    force: bool = False


@router.post("/level/create-cell")
async def create_cell(request: CellCreateRequest):
    try:
        cell_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        cell = {
            "id": cell_id,
            "name": request.name,
            "bounds": request.bounds,
            "priority": request.priority,
            "metadata": request.metadata or {},
            "loaded": False,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        _cells[cell_id] = cell

        return {"status": "success", "data": cell}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/level/cells")
async def list_cells():
    try:
        cells_list = list(_cells.values())
        return {
            "status": "success",
            "data": {
                "cells": cells_list,
                "total_count": len(cells_list),
                "loaded_count": len(
                    [c for c in cells_list if c.get("loaded")]
                ),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/level/load-cell")
async def load_cell(request: CellLoadRequest):
    try:
        cell = _cells.get(request.cell_id)
        if not cell:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Cell not found"},
            )

        if cell.get("loaded"):
            return {
                "status": "success",
                "data": {
                    "cell_id": request.cell_id,
                    "already_loaded": True,
                },
            }

        cell["loaded"] = True
        cell["updated_at"] = datetime.utcnow().isoformat()
        cell["priority"] = request.priority

        if request.cell_id not in _streaming_state["loaded_cells"]:
            _streaming_state["loaded_cells"].append(request.cell_id)

        return {
            "status": "success",
            "data": {
                "cell_id": request.cell_id,
                "loaded": True,
                "active_loaded_count": len(_streaming_state["loaded_cells"]),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/level/unload-cell")
async def unload_cell(request: CellUnloadRequest):
    try:
        cell = _cells.get(request.cell_id)
        if not cell:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Cell not found"},
            )

        if not cell.get("loaded") and not request.force:
            return {
                "status": "success",
                "data": {
                    "cell_id": request.cell_id,
                    "already_unloaded": True,
                },
            }

        cell["loaded"] = False
        cell["updated_at"] = datetime.utcnow().isoformat()

        if request.cell_id in _streaming_state["loaded_cells"]:
            _streaming_state["loaded_cells"].remove(request.cell_id)

        return {
            "status": "success",
            "data": {
                "cell_id": request.cell_id,
                "unloaded": True,
                "remaining_loaded": len(_streaming_state["loaded_cells"]),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/level/streaming-status")
async def get_streaming_status():
    try:
        loaded_cells = [
            _cells[cid]
            for cid in _streaming_state["loaded_cells"]
            if cid in _cells
        ]
        pending_cells = [
            _cells[cid]
            for cid in _streaming_state["pending_cells"]
            if cid in _cells
        ]

        return {
            "status": "success",
            "data": {
                "active": _streaming_state["active"],
                "stream_budget": _streaming_state["stream_budget"],
                "loaded_cells": loaded_cells,
                "pending_cells": pending_cells,
                "loaded_count": len(loaded_cells),
                "pending_count": len(pending_cells),
                "total_cells": len(_cells),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )