"""
SparkAI Workflow - Executor Engine
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from sparkai.workflow.graph import WorkflowGraph, WorkflowNode


class WorkflowExecutor:
    """
    Executes workflow graphs in topological order.
    Each node's output is passed to connected nodes as input.
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}
        self._running = False

    async def execute(self, graph: WorkflowGraph) -> Dict[str, Any]:
        self._running = True
        self._results = {}

        order = graph.get_execution_order()
        all_results: Dict[str, Any] = {}

        for node_id in order:
            if not self._running:
                break

            node = graph.get_node(node_id)
            if not node:
                continue

            inputs = self._gather_inputs(graph, node_id)
            result = await self._execute_node(node, inputs)
            self._results[node_id] = result
            all_results[node_id] = result

        self._running = False
        return all_results

    def stop(self) -> None:
        self._running = False

    def _gather_inputs(self, graph: WorkflowGraph, node_id: str) -> Dict[str, Any]:
        inputs: Dict[str, Any] = {}
        for edge in graph.get_edges():
            if edge.target_node_id == node_id:
                source_result = self._results.get(edge.source_node_id, {})
                if isinstance(source_result, dict):
                    output_key = f"output_{edge.source_pin_index}"
                    inputs[f"input_{edge.target_pin_index}"] = source_result.get(output_key, source_result)
                else:
                    inputs[f"input_{edge.target_pin_index}"] = source_result
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
            return {"output_0": {"type": "branch", "condition": props.get("condition", True)}}
        elif node_type == "scene_create":
            return {"output_0": {"type": "scene", "name": props.get("name", ""), "status": "created"}}
        elif node_type == "entity_create":
            return {"output_0": {"type": "entity", "name": props.get("name", ""), "status": "created"}}
        elif node_type == "npc_create":
            return {"output_0": {"type": "npc", "name": props.get("name", ""), "status": "created"}}
        else:
            return {"output_0": {"type": node_type, "status": "executed", "inputs": inputs}}
