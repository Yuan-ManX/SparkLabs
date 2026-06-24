"""
SparkLabs Backend - Unified Orchestration & Runtime Routes

API endpoints for the unified orchestration core (task management,
pipeline coordination, subsystem health, resource allocation) and
the unified game runtime (game loop control, scene management,
rendering, physics, audio, input, and entity coordination).
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory storage for orchestration
# ---------------------------------------------------------------------------

_orchestration_initialized: bool = False
_submitted_tasks: Dict[str, Dict[str, Any]] = {}
_active_workflows: Dict[str, Dict[str, Any]] = {}
_subsystem_health: Dict[str, Dict[str, Any]] = {
    "cognitive_synthesis": {"status": "healthy", "success_rate": 0.98, "active_tasks": 0},
    "game_intelligence": {"status": "healthy", "success_rate": 0.95, "active_tasks": 0},
    "autonomous_creator": {"status": "healthy", "success_rate": 0.97, "active_tasks": 0},
    "interaction_loop": {"status": "healthy", "success_rate": 0.99, "active_tasks": 0},
    "swarm_intelligence": {"status": "healthy", "success_rate": 0.94, "active_tasks": 0},
    "llm_pipeline": {"status": "healthy", "success_rate": 0.96, "active_tasks": 0},
    "game_creator": {"status": "healthy", "success_rate": 0.93, "active_tasks": 0},
    "behavior_designer": {"status": "healthy", "success_rate": 0.97, "active_tasks": 0},
    "dialogue_engine": {"status": "healthy", "success_rate": 0.98, "active_tasks": 0},
    "quest_generator": {"status": "healthy", "success_rate": 0.96, "active_tasks": 0},
    "world_simulator": {"status": "healthy", "success_rate": 0.95, "active_tasks": 0},
    "story_engine": {"status": "healthy", "success_rate": 0.97, "active_tasks": 0},
    "game_designer": {"status": "healthy", "success_rate": 0.94, "active_tasks": 0},
    "player_modeler": {"status": "healthy", "success_rate": 0.96, "active_tasks": 0},
    "balance_optimizer": {"status": "healthy", "success_rate": 0.93, "active_tasks": 0},
    "performance_optimizer": {"status": "healthy", "success_rate": 0.95, "active_tasks": 0},
    "emotion_engine": {"status": "healthy", "success_rate": 0.98, "active_tasks": 0},
    "social_cognition": {"status": "healthy", "success_rate": 0.97, "active_tasks": 0},
    "perception_fusion": {"status": "healthy", "success_rate": 0.96, "active_tasks": 0},
    "learning_loop": {"status": "healthy", "success_rate": 0.94, "active_tasks": 0},
}

# ---------------------------------------------------------------------------
# In-memory storage for runtime
# ---------------------------------------------------------------------------

_runtime_initialized: bool = False
_runtime_state: str = "stopped"
_frame_count: int = 0
_elapsed_time: float = 0.0
_fps: float = 0.0
_scenes: Dict[str, Dict[str, Any]] = {}
_entities: Dict[str, Dict[str, Any]] = {}
_frame_history: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TaskSubmitRequest(BaseModel):
    name: str
    target_subsystem: str = "cognitive_synthesis"
    priority: str = "medium"
    payload: Dict[str, Any] = {}


class PipelineCreateRequest(BaseModel):
    pipeline_type: str = "game_creation"
    name: str = ""


class RuntimeConfigRequest(BaseModel):
    fixed_timestep: float = 0.016667
    time_scale: float = 1.0


class SceneCreateRequest(BaseModel):
    name: str
    environment_settings: Dict[str, Any] = {}


class EntityCreateRequest(BaseModel):
    name: str = ""
    components: Dict[str, Any] = {}


class InputUpdateRequest(BaseModel):
    input_name: str
    value: Any


# ---------------------------------------------------------------------------
# Orchestration endpoints
# ---------------------------------------------------------------------------

@router.post("/orchestration/initialize")
async def initialize_orchestration():
    try:
        global _orchestration_initialized
        _orchestration_initialized = True
        return {
            "status": "success",
            "data": {
                "initialized": True,
                "subsystems": len(_subsystem_health),
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/orchestration/task")
async def submit_task(request: TaskSubmitRequest):
    try:
        task_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        task = {
            "task_id": task_id,
            "name": request.name,
            "target_subsystem": request.target_subsystem,
            "priority": request.priority,
            "status": "dispatched",
            "payload": request.payload,
            "created_at": timestamp,
            "dispatched_at": timestamp,
        }

        _submitted_tasks[task_id] = task

        if request.target_subsystem in _subsystem_health:
            _subsystem_health[request.target_subsystem]["active_tasks"] += 1

        return {"status": "success", "data": task}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/orchestration/task/{task_id}/complete")
async def complete_task(task_id: str, success: bool = True, result: Optional[Dict[str, Any]] = None):
    try:
        task = _submitted_tasks.get(task_id)
        if not task:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Task not found"})

        task["status"] = "completed" if success else "failed"
        task["result"] = result or {}
        task["completed_at"] = datetime.utcnow().isoformat()

        subsystem = task["target_subsystem"]
        if subsystem in _subsystem_health:
            _subsystem_health[subsystem]["active_tasks"] = max(0, _subsystem_health[subsystem]["active_tasks"] - 1)
            if success:
                _subsystem_health[subsystem]["success_rate"] = min(1.0, _subsystem_health[subsystem]["success_rate"] + 0.001)
            else:
                _subsystem_health[subsystem]["success_rate"] = max(0.0, _subsystem_health[subsystem]["success_rate"] - 0.01)

        return {"status": "success", "data": task}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/orchestration/tasks")
async def list_tasks(status: Optional[str] = Query(None)):
    try:
        tasks = list(_submitted_tasks.values())
        if status:
            tasks = [t for t in tasks if t.get("status") == status]

        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {
            "status": "success",
            "data": {
                "tasks": tasks,
                "total_count": len(tasks),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/orchestration/pipeline")
async def create_pipeline(request: PipelineCreateRequest):
    try:
        pipeline_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        pipeline_types = {
            "game_creation": [
                "concept_design", "story_development", "world_building",
                "content_generation", "quest_design", "dialogue_writing",
                "behavior_setup", "balance_testing", "performance_review",
                "quality_evaluation",
            ],
            "content_generation": [
                "requirement_analysis", "level_design", "npc_creation",
                "item_design", "quality_check",
            ],
            "intelligence_analysis": [
                "data_collection", "pattern_analysis", "game_evaluation",
                "optimization_planning", "learning_feedback",
            ],
        }

        stages_def = pipeline_types.get(request.pipeline_type, pipeline_types["game_creation"])
        stages = []
        for i, stage_name in enumerate(stages_def):
            stages.append({
                "stage_id": str(uuid.uuid4()),
                "name": stage_name,
                "order": i,
                "status": "pending",
                "depends_on": [stages[i - 1]["stage_id"]] if i > 0 else [],
            })

        pipeline = {
            "pipeline_id": pipeline_id,
            "name": request.name or f"{request.pipeline_type}_{uuid.uuid4().hex[:8]}",
            "type": request.pipeline_type,
            "stages": stages,
            "current_stage": 0,
            "total_stages": len(stages),
            "status": "pending",
            "created_at": timestamp,
        }

        _active_workflows[pipeline_id] = pipeline

        return {"status": "success", "data": pipeline}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/orchestration/pipeline/{pipeline_id}/advance")
async def advance_pipeline(pipeline_id: str):
    try:
        pipeline = _active_workflows.get(pipeline_id)
        if not pipeline:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Pipeline not found"})

        if pipeline["current_stage"] < len(pipeline["stages"]):
            pipeline["stages"][pipeline["current_stage"]]["status"] = "completed"
            pipeline["stages"][pipeline["current_stage"]]["completed_at"] = datetime.utcnow().isoformat()
            pipeline["current_stage"] += 1

            if pipeline["current_stage"] < len(pipeline["stages"]):
                pipeline["stages"][pipeline["current_stage"]]["status"] = "in_progress"
                pipeline["status"] = "in_progress"
            else:
                pipeline["status"] = "completed"
                pipeline["completed_at"] = datetime.utcnow().isoformat()

        return {"status": "success", "data": pipeline}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/orchestration/pipelines")
async def list_pipelines():
    try:
        pipelines = list(_active_workflows.values())
        return {
            "status": "success",
            "data": {
                "pipelines": pipelines,
                "total_count": len(pipelines),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/orchestration/health")
async def get_orchestration_health():
    try:
        return {
            "status": "success",
            "data": {
                "initialized": _orchestration_initialized,
                "subsystems": _subsystem_health,
                "active_tasks": len([t for t in _submitted_tasks.values() if t["status"] in ("dispatched", "in_progress")]),
                "active_workflows": len(_active_workflows),
                "total_tasks": len(_submitted_tasks),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/orchestration/report")
async def get_orchestration_report():
    try:
        completed = sum(1 for t in _submitted_tasks.values() if t["status"] == "completed")
        failed = sum(1 for t in _submitted_tasks.values() if t["status"] == "failed")

        return {
            "status": "success",
            "data": {
                "total_tasks": len(_submitted_tasks),
                "completed_tasks": completed,
                "failed_tasks": failed,
                "active_workflows": len(_active_workflows),
                "subsystem_health": _subsystem_health,
                "performance_metrics": {
                    "avg_success_rate": round(
                        sum(s["success_rate"] for s in _subsystem_health.values()) / max(len(_subsystem_health), 1), 4
                    ),
                    "total_active_tasks": sum(s["active_tasks"] for s in _subsystem_health.values()),
                },
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Runtime endpoints
# ---------------------------------------------------------------------------

@router.post("/runtime/initialize")
async def initialize_runtime(request: RuntimeConfigRequest):
    try:
        global _runtime_initialized, _runtime_state, _frame_count, _elapsed_time
        _runtime_initialized = True
        _runtime_state = "stopped"
        _frame_count = 0
        _elapsed_time = 0.0

        return {
            "status": "success",
            "data": {
                "initialized": True,
                "fixed_timestep": request.fixed_timestep,
                "time_scale": request.time_scale,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/runtime/start")
async def start_runtime():
    try:
        global _runtime_state
        _runtime_state = "running"
        return {
            "status": "success",
            "data": {"state": _runtime_state, "timestamp": datetime.utcnow().isoformat()},
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/runtime/pause")
async def pause_runtime():
    try:
        global _runtime_state
        _runtime_state = "paused"
        return {
            "status": "success",
            "data": {"state": _runtime_state, "timestamp": datetime.utcnow().isoformat()},
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/runtime/stop")
async def stop_runtime():
    try:
        global _runtime_state
        _runtime_state = "stopped"
        return {
            "status": "success",
            "data": {"state": _runtime_state, "timestamp": datetime.utcnow().isoformat()},
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/runtime/tick")
async def tick_runtime(delta_time: float = 0.016667):
    try:
        global _frame_count, _elapsed_time, _fps, _frame_history

        if _runtime_state != "running":
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": f"Runtime is not running (state: {_runtime_state})"},
            )

        _frame_count += 1
        _elapsed_time += delta_time

        if _frame_count % 10 == 0:
            recent = _frame_history[-10:] if _frame_history else []
            if recent:
                avg_dt = sum(f.get("delta_time", 0.016667) for f in recent) / len(recent)
                _fps = 1.0 / max(avg_dt, 0.0001)
            else:
                _fps = 1.0 / max(delta_time, 0.0001)

        frame_data = {
            "frame_id": _frame_count,
            "delta_time": delta_time,
            "elapsed_time": _elapsed_time,
            "fps": round(_fps, 1),
            "timestamp": datetime.utcnow().isoformat(),
        }
        _frame_history.append(frame_data)

        return {
            "status": "success",
            "data": {
                "frame_timing": frame_data,
                "render_stats": {
                    "draw_calls": _frame_count * 10,
                    "triangles": _frame_count * 100,
                },
                "physics_stats": {
                    "bodies": len(_entities),
                    "contacts": len(_entities) * 2,
                },
                "active_entities": len(_entities),
                "active_scenes": len(_scenes),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/runtime/status")
async def get_runtime_status():
    try:
        return {
            "status": "success",
            "data": {
                "state": _runtime_state,
                "initialized": _runtime_initialized,
                "frame_count": _frame_count,
                "elapsed_time": round(_elapsed_time, 4),
                "fps": round(_fps, 1),
                "entities": len(_entities),
                "scenes": len(_scenes),
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/runtime/scene")
async def create_scene(request: SceneCreateRequest):
    try:
        scene_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        scene = {
            "scene_id": scene_id,
            "name": request.name,
            "state": "created",
            "entities": [],
            "environment_settings": request.environment_settings,
            "created_at": timestamp,
        }

        _scenes[scene_id] = scene

        return {"status": "success", "data": scene}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/runtime/scenes")
async def list_scenes():
    try:
        scenes = list(_scenes.values())
        return {
            "status": "success",
            "data": {
                "scenes": scenes,
                "total_count": len(scenes),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/runtime/entity")
async def create_entity(request: EntityCreateRequest):
    try:
        entity_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        entity = {
            "entity_id": entity_id,
            "name": request.name or f"Entity_{entity_id[:6]}",
            "components": request.components,
            "active": True,
            "created_at": timestamp,
        }

        _entities[entity_id] = entity

        return {"status": "success", "data": entity}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/runtime/entities")
async def list_entities():
    try:
        entities = list(_entities.values())
        return {
            "status": "success",
            "data": {
                "entities": entities,
                "total_count": len(entities),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/runtime/input")
async def update_input(request: InputUpdateRequest):
    try:
        return {
            "status": "success",
            "data": {
                "input_name": request.input_name,
                "value": request.value,
                "processed": True,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/runtime/profile")
async def get_runtime_profile():
    try:
        recent_frames = _frame_history[-60:] if _frame_history else []

        bottlenecks = []
        if _fps < 30:
            bottlenecks.append({"type": "render_bound", "severity": "high"})
        elif _fps < 50:
            bottlenecks.append({"type": "render_bound", "severity": "medium"})

        return {
            "status": "success",
            "data": {
                "frame_timing": {
                    "frame_count": _frame_count,
                    "fps": round(_fps, 1),
                    "elapsed_time": round(_elapsed_time, 4),
                },
                "recent_frames": recent_frames[-10:],
                "bottlenecks": bottlenecks,
                "active_entities": len(_entities),
                "active_scenes": len(_scenes),
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})