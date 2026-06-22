"""
SparkLabs Backend - Workflow Routes
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from sparkai.workflow.graph import WorkflowGraph, WorkflowNode, PinType
from sparkai.workflow.executor import WorkflowExecutor
from sparkai.workflow.registry import NodeRegistry

router = APIRouter()

_workflows: Dict[str, WorkflowGraph] = {}
_executor = WorkflowExecutor()


class WorkflowCreateRequest(BaseModel):
    name: str = "Untitled Workflow"


class NodeCreateRequest(BaseModel):
    workflow_id: str
    node_type: str
    name: Optional[str] = None
    position: List[float] = [0, 0]
    properties: Optional[Dict[str, Any]] = None


class ConnectRequest(BaseModel):
    workflow_id: str
    source_node_id: str
    source_pin: int = 0
    target_node_id: str
    target_pin: int = 0


class ExecuteRequest(BaseModel):
    workflow_id: str


@router.post("/create")
async def create_workflow(request: WorkflowCreateRequest):
    try:
        graph = WorkflowGraph(name=request.name)
        _workflows[graph.id] = graph
        return {"status": "success", "data": graph.to_dict()}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/list")
async def list_workflows():
    try:
        return {
            "status": "success",
            "data": {"workflows": [w.to_dict() for w in _workflows.values()]},
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/node-types")
async def list_node_types():
    try:
        registry = NodeRegistry.get_instance()
        return {
            "status": "success",
            "data": {
                "node_types": registry.list_node_types(),
                "categories": registry.list_categories(),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    try:
        graph = _workflows.get(workflow_id)
        if graph:
            return {"status": "success", "data": graph.to_dict()}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Workflow not found"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/node/create")
async def create_node(request: NodeCreateRequest):
    try:
        graph = _workflows.get(request.workflow_id)
        if not graph:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Workflow not found"},
            )

        registry = NodeRegistry.get_instance()
        node = registry.create_node(request.node_type, name=request.name)
        if not node:
            node = WorkflowNode(
                name=request.name or request.node_type,
                node_type=request.node_type,
                position=request.position,
                properties=request.properties or {},
            )
        else:
            node.position = request.position
            if request.properties:
                for k, v in request.properties.items():
                    node.set_property(k, v)

        graph.add_node(node)
        return {"status": "success", "data": node.to_dict()}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/connect")
async def connect_nodes(request: ConnectRequest):
    try:
        graph = _workflows.get(request.workflow_id)
        if not graph:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Workflow not found"},
            )
        edge = graph.connect(
            request.source_node_id,
            request.source_pin,
            request.target_node_id,
            request.target_pin,
        )
        if edge:
            return {
                "status": "success",
                "data": {
                    "edge_id": edge.id,
                    "source": edge.source_node_id,
                    "target": edge.target_node_id,
                },
            }
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Connection failed"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/execute")
async def execute_workflow(request: ExecuteRequest):
    try:
        graph = _workflows.get(request.workflow_id)
        if not graph:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Workflow not found"},
            )
        results = await _executor.execute(graph)
        return {"status": "success", "data": {"results": results}}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    try:
        if workflow_id in _workflows:
            del _workflows[workflow_id]
            return {"status": "success", "data": {"success": True}}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Workflow not found"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )