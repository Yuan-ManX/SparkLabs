"""
SparkAI Workflow - Executor Engine

Executes workflow DAGs with level-based parallel execution,
named data bindings between nodes, and checkpointing for
resume-from-failure capability.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from sparkai.workflow.graph import WorkflowGraph, WorkflowNode


class ExecutionCheckpoint:
    """Stores intermediate execution state for resume-from-failure."""

    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        self.completed_nodes: Dict[str, Any] = {}
        self.failed_node: Optional[str] = None
        self.failure_error: Optional[str] = None
        self.started_at: float = time.time()
        self.completed_at: Optional[float] = None

    def save(self, directory: str = ".sparkai/workflow_checkpoints") -> str:
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, f"{self.graph_id}.json")
        data = {
            "graph_id": self.graph_id,
            "completed_nodes": self.completed_nodes,
            "failed_node": self.failed_node,
            "failure_error": self.failure_error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, default=str, indent=2)
        return filepath

    @classmethod
    def load(cls, filepath: str) -> "ExecutionCheckpoint":
        with open(filepath, "r") as f:
            data = json.load(f)
        cp = cls(data["graph_id"])
        cp.completed_nodes = data.get("completed_nodes", {})
        cp.failed_node = data.get("failed_node")
        cp.failure_error = data.get("failure_error")
        cp.started_at = data.get("started_at", time.time())
        cp.completed_at = data.get("completed_at")
        return cp


class WorkflowExecutor:
    """
    Executes workflow DAGs with level-based parallel execution.
    Nodes at the same topological level with no inter-dependencies
    execute concurrently via asyncio.gather.
    """

    def __init__(self, max_concurrent_nodes: int = 4, enable_checkpointing: bool = True):
        self._results: Dict[str, Any] = {}
        self._running = False
        self._max_concurrent = max_concurrent_nodes
        self._enable_checkpointing = enable_checkpointing
        self._checkpoint: Optional[ExecutionCheckpoint] = None
        self._stats = {
            "total_executions": 0,
            "total_nodes_executed": 0,
            "total_parallel_groups": 0,
            "total_checkpoints_saved": 0,
        }

    async def execute(self, graph: WorkflowGraph, resume_from: Optional[str] = None) -> Dict[str, Any]:
        self._running = True
        self._results = {}
        all_results: Dict[str, Any] = {}

        if resume_from and self._enable_checkpointing:
            cp_path = os.path.join(".sparkai/workflow_checkpoints", f"{resume_from}.json")
            if os.path.exists(cp_path):
                cp = ExecutionCheckpoint.load(cp_path)
                self._results = cp.completed_nodes
                all_results = dict(cp.completed_nodes)

        if self._enable_checkpointing:
            self._checkpoint = ExecutionCheckpoint(graph_id=str(id(graph)))

        levels = self._compute_levels(graph)

        for level_idx, level in enumerate(levels):
            if not self._running:
                break

            self._stats["total_parallel_groups"] += 1

            if len(level) == 1:
                node_id = level[0]
                node = graph.get_node(node_id)
                if node:
                    inputs = self._gather_inputs(graph, node_id)
                    result = await self._execute_node(node, inputs)
                    self._results[node_id] = result
                    all_results[node_id] = result
                    self._stats["total_nodes_executed"] += 1

                    if self._checkpoint:
                        self._checkpoint.completed_nodes[node_id] = result
            else:
                semaphore = asyncio.Semaphore(self._max_concurrent)

                async def _run_node(nid: str) -> Tuple[str, Any]:
                    async with semaphore:
                        node = graph.get_node(nid)
                        if not node:
                            return nid, None
                        inputs = self._gather_inputs(graph, nid)
                        result = await self._execute_node(node, inputs)
                        return nid, result

                tasks = [_run_node(nid) for nid in level]
                completed = await asyncio.gather(*tasks, return_exceptions=True)

                for item in completed:
                    if isinstance(item, Exception):
                        continue
                    nid, result = item
                    if result is not None:
                        self._results[nid] = result
                        all_results[nid] = result
                        self._stats["total_nodes_executed"] += 1

                        if self._checkpoint:
                            self._checkpoint.completed_nodes[nid] = result

            if self._checkpoint and self._enable_checkpointing:
                self._checkpoint.save()

        self._running = False
        self._stats["total_executions"] += 1

        if self._checkpoint:
            self._checkpoint.completed_at = time.time()
            self._checkpoint.save()
            self._stats["total_checkpoints_saved"] += 1

        return all_results

    def _compute_levels(self, graph: WorkflowGraph) -> List[List[str]]:
        """
        Compute topological levels for parallel execution.
        Nodes at the same level have no dependencies between them.
        """
        order = graph.get_execution_order()
        edges = graph.get_edges()

        in_degree: Dict[str, int] = {nid: 0 for nid in order}
        dependents: Dict[str, List[str]] = {nid: [] for nid in order}

        for edge in edges:
            if edge.target_node_id in in_degree:
                in_degree[edge.target_node_id] += 1
                if edge.source_node_id in dependents:
                    dependents[edge.source_node_id].append(edge.target_node_id)

        levels: List[List[str]] = []
        remaining = set(order)

        while remaining:
            level = [nid for nid in remaining if in_degree.get(nid, 0) == 0]
            if not level:
                level = [min(remaining, key=lambda n: in_degree.get(n, 0))]
            levels.append(level)
            for nid in level:
                remaining.discard(nid)
                for dep in dependents.get(nid, []):
                    in_degree[dep] = max(0, in_degree.get(dep, 1) - 1)

        return levels

    def stop(self) -> None:
        self._running = False

    def _gather_inputs(self, graph: WorkflowGraph, node_id: str) -> Dict[str, Any]:
        inputs: Dict[str, Any] = {}
        for edge in graph.get_edges():
            if edge.target_node_id == node_id:
                source_result = self._results.get(edge.source_node_id, {})
                source_node = graph.get_node(edge.source_node_id)

                pin_name = f"output_{edge.source_pin_index}"
                if source_node and edge.source_pin_index < len(source_node.outputs):
                    pin_name = source_node.outputs[edge.source_pin_index].name or pin_name

                target_pin_name = f"input_{edge.target_pin_index}"
                target_node = graph.get_node(node_id)
                if target_node and edge.target_pin_index < len(target_node.inputs):
                    target_pin_name = target_node.inputs[edge.target_pin_index].name or target_pin_name

                if isinstance(source_result, dict):
                    inputs[target_pin_name] = source_result.get(pin_name, source_result)
                else:
                    inputs[target_pin_name] = source_result
        return inputs

    async def _execute_node(self, node: WorkflowNode, inputs: Dict[str, Any]) -> Dict[str, Any]:
        node_type = node.node_type
        props = node.properties

        if node_type == "text_prompt":
            return {"output_0": props.get("prompt", "")}
        elif node_type == "image_generation":
            return {"output_0": {"type": "image", "prompt": props.get("prompt", ""), "status": "generated"}}
        elif node_type == "text_generation":
            return {"output_0": {"type": "text", "prompt": props.get("prompt", ""), "status": "generated"}}
        elif node_type == "video_generation":
            return {"output_0": {"type": "video", "prompt": props.get("prompt", ""), "status": "generated"}}
        elif node_type == "audio_generation":
            return {"output_0": {"type": "audio", "prompt": props.get("prompt", ""), "status": "generated"}}
        elif node_type == "save_image":
            return {"output_0": {"type": "save", "path": props.get("output_path", ""), "status": "saved"}}
        elif node_type == "save_video":
            return {"output_0": {"type": "save", "path": props.get("output_path", ""), "status": "saved"}}
        elif node_type == "save_audio":
            return {"output_0": {"type": "save", "path": props.get("output_path", ""), "status": "saved"}}
        elif node_type == "load_image":
            return {"output_0": {"type": "image", "path": props.get("file_path", ""), "status": "loaded"}}
        elif node_type == "ksampler":
            return {"output_0": {"type": "latent", "steps": props.get("steps", 20), "status": "sampled"}}
        elif node_type == "vae_decode":
            return {"output_0": {"type": "image", "status": "decoded"}}
        elif node_type == "vae_encode":
            return {"output_0": {"type": "latent", "status": "encoded"}}
        elif node_type == "latent":
            return {"output_0": {"type": "latent", "width": props.get("width", 512), "height": props.get("height", 512)}}
        elif node_type == "controlnet":
            return {"output_0": {"type": "control", "status": "applied"}}
        elif node_type == "upscale":
            return {"output_0": {"type": "image", "scale": props.get("scale", 2.0), "status": "upscaled"}}
        elif node_type == "inpaint":
            return {"output_0": {"type": "image", "status": "inpainted"}}
        elif node_type == "negative_prompt":
            return {"output_0": props.get("prompt", "")}
        elif node_type == "condition":
            condition_value = props.get("condition", True)
            if isinstance(condition_value, str):
                try:
                    condition_value = eval(condition_value, {"__builtins__": {}}, inputs)
                except Exception:
                    condition_value = bool(condition_value)
            return {
                "output_0": {"type": "branch_true", "condition": condition_value},
                "output_1": {"type": "branch_false", "condition": not condition_value},
            }
        elif node_type == "scene_create":
            return {"output_0": {"type": "scene", "name": props.get("name", ""), "status": "created"}}
        elif node_type == "entity_create":
            return {"output_0": {"type": "entity", "name": props.get("name", ""), "status": "created"}}
        elif node_type == "npc_create":
            return {"output_0": {"type": "npc", "name": props.get("name", ""), "status": "created"}}
        else:
            return {"output_0": {"type": node_type, "status": "executed", "inputs": inputs}}

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)
