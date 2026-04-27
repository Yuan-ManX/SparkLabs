"""
SparkLabs Backend - Workflow Routes
"""

from fastapi import APIRouter
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
    graph = WorkflowGraph(name=request.name)
    _workflows[graph.id] = graph
    return graph.to_dict()


@router.get("/list")
async def list_workflows():
    return {"workflows": [w.to_dict() for w in _workflows.values()]}


@router.get("/node-types")
async def list_node_types():
    registry = NodeRegistry.get_instance()
    return {"node_types": registry.list_node_types(), "categories": registry.list_categories()}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    graph = _workflows.get(workflow_id)
    if graph:
        return graph.to_dict()
    return {"error": "Workflow not found"}


@router.post("/node/create")
async def create_node(request: NodeCreateRequest):
    graph = _workflows.get(request.workflow_id)
    if not graph:
        return {"error": "Workflow not found"}

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
    return node.to_dict()


@router.post("/connect")
async def connect_nodes(request: ConnectRequest):
    graph = _workflows.get(request.workflow_id)
    if not graph:
        return {"error": "Workflow not found"}
    edge = graph.connect(
        request.source_node_id,
        request.source_pin,
        request.target_node_id,
        request.target_pin,
    )
    if edge:
        return {
            "edge_id": edge.id,
            "source": edge.source_node_id,
            "target": edge.target_node_id,
        }
    return {"error": "Connection failed"}


@router.post("/execute")
async def execute_workflow(request: ExecuteRequest):
    graph = _workflows.get(request.workflow_id)
    if not graph:
        return {"error": "Workflow not found"}
    results = await _executor.execute(graph)
    return {"results": results}


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    if workflow_id in _workflows:
        del _workflows[workflow_id]
        return {"success": True}
    return {"error": "Workflow not found"}
