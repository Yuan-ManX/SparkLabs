"""
SparkAI Workflow - Node Registry
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sparkai.workflow.graph import WorkflowNode, PinType


class NodeRegistry:
    """
    Registry for workflow node types.
    Provides factory methods for creating typed nodes.
    """

    _instance: Optional["NodeRegistry"] = None

    def __init__(self):
        self._node_types: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_nodes()

    @classmethod
    def get_instance(cls) -> "NodeRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_node_type(
        self,
        node_type: str,
        category: str,
        name: str,
        input_pins: Optional[List[Dict]] = None,
        output_pins: Optional[List[Dict]] = None,
        default_properties: Optional[Dict] = None,
    ) -> None:
        self._node_types[node_type] = {
            "category": category,
            "name": name,
            "input_pins": input_pins or [],
            "output_pins": output_pins or [],
            "default_properties": default_properties or {},
        }

    def create_node(
        self, node_type: str, name: Optional[str] = None
    ) -> Optional[WorkflowNode]:
        type_def = self._node_types.get(node_type)
        if not type_def:
            return None

        node = WorkflowNode(
            name=name or type_def["name"],
            category=type_def["category"],
            node_type=node_type,
            properties=dict(type_def["default_properties"]),
        )

        for pin_def in type_def["input_pins"]:
            node.add_input_pin(
                name=pin_def.get("name", "input"),
                pin_type=PinType(pin_def.get("type", "any")),
            )

        for pin_def in type_def["output_pins"]:
            node.add_output_pin(
                name=pin_def.get("name", "output"),
                pin_type=PinType(pin_def.get("type", "any")),
            )

        return node

    def list_node_types(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        types = []
        for node_type, type_def in self._node_types.items():
            if category and type_def["category"] != category:
                continue
            types.append({
                "type": node_type,
                "name": type_def["name"],
                "category": type_def["category"],
            })
        return types

    def list_categories(self) -> List[str]:
        return list(set(t["category"] for t in self._node_types.values()))

    def _register_builtin_nodes(self) -> None:
        prompt_pins_out = [{"name": "text", "type": "text"}]
        image_pins_in = [{"name": "prompt", "type": "text"}]
        image_pins_out = [{"name": "image", "type": "image"}]

        self.register_node_type("text_prompt", "Prompt", "Text Prompt",
                                output_pins=prompt_pins_out,
                                default_properties={"prompt": ""})

        self.register_node_type("negative_prompt", "Prompt", "Negative Prompt",
                                output_pins=[{"name": "text", "type": "text"}],
                                default_properties={"prompt": ""})

        self.register_node_type("image_generation", "AI/Image", "Image Generation",
                                input_pins=image_pins_in,
                                output_pins=image_pins_out,
                                default_properties={"model": "", "width": 1024, "height": 1024, "steps": 30, "guidance_scale": 7.5, "seed": -1})

        self.register_node_type("text_generation", "AI/Text", "Text Generation",
                                input_pins=[{"name": "prompt", "type": "text"}],
                                output_pins=[{"name": "text", "type": "text"}],
                                default_properties={"model": "", "max_tokens": 512, "temperature": 0.7})

        self.register_node_type("video_generation", "AI/Video", "Video Generation",
                                input_pins=[{"name": "prompt", "type": "text"}],
                                output_pins=[{"name": "video", "type": "video"}],
                                default_properties={"model": "", "duration": 10, "fps": 30})

        self.register_node_type("audio_generation", "AI/Audio", "Audio Generation",
                                input_pins=[{"name": "prompt", "type": "text"}],
                                output_pins=[{"name": "audio", "type": "audio"}],
                                default_properties={"model": "", "duration": 10.0, "sample_rate": 44100})

        self.register_node_type("save_image", "Output", "Save Image",
                                input_pins=[{"name": "image", "type": "image"}],
                                output_pins=[{"name": "path", "type": "text"}],
                                default_properties={"output_path": "output/image.png"})

        self.register_node_type("save_video", "Output", "Save Video",
                                input_pins=[{"name": "video", "type": "video"}],
                                output_pins=[{"name": "path", "type": "text"}],
                                default_properties={"output_path": "output/video.mp4"})

        self.register_node_type("save_audio", "Output", "Save Audio",
                                input_pins=[{"name": "audio", "type": "audio"}],
                                output_pins=[{"name": "path", "type": "text"}],
                                default_properties={"output_path": "output/audio.wav"})

        self.register_node_type("load_image", "Input", "Load Image",
                                output_pins=[{"name": "image", "type": "image"}],
                                default_properties={"file_path": ""})

        self.register_node_type("ksampler", "Sampling", "KSampler",
                                input_pins=[{"name": "model", "type": "model"}, {"name": "positive", "type": "any"}, {"name": "negative", "type": "any"}, {"name": "latent", "type": "any"}],
                                output_pins=[{"name": "latent", "type": "any"}],
                                default_properties={"steps": 20, "cfg": 8.0, "seed": 0, "sampler_name": "euler_a"})

        self.register_node_type("vae_decode", "Latent", "VAE Decode",
                                input_pins=[{"name": "samples", "type": "any"}, {"name": "vae", "type": "model"}],
                                output_pins=[{"name": "image", "type": "image"}])

        self.register_node_type("vae_encode", "Latent", "VAE Encode",
                                input_pins=[{"name": "pixels", "type": "image"}, {"name": "vae", "type": "model"}],
                                output_pins=[{"name": "latent", "type": "any"}])

        self.register_node_type("latent", "Latent", "Empty Latent",
                                output_pins=[{"name": "latent", "type": "any"}],
                                default_properties={"width": 512, "height": 512, "batch_size": 1})

        self.register_node_type("controlnet", "ControlNet", "ControlNet Apply",
                                input_pins=[{"name": "conditioning", "type": "any"}, {"name": "image", "type": "image"}],
                                output_pins=[{"name": "conditioning", "type": "any"}],
                                default_properties={"strength": 1.0})

        self.register_node_type("upscale", "AI/Image", "Upscale",
                                input_pins=[{"name": "image", "type": "image"}],
                                output_pins=[{"name": "image", "type": "image"}],
                                default_properties={"method": "nearest", "scale": 2.0})

        self.register_node_type("inpaint", "AI/Image", "Inpaint",
                                input_pins=[{"name": "image", "type": "image"}, {"name": "mask", "type": "image"}],
                                output_pins=[{"name": "image", "type": "image"}],
                                default_properties={"prompt": ""})

        self.register_node_type("condition", "Logic", "Condition",
                                input_pins=[{"name": "input", "type": "any"}],
                                output_pins=[{"name": "true", "type": "any"}, {"name": "false", "type": "any"}],
                                default_properties={"condition": True})

        self.register_node_type("scene_create", "Game", "Create Scene",
                                output_pins=[{"name": "scene", "type": "any"}],
                                default_properties={"name": "New Scene"})

        self.register_node_type("entity_create", "Game", "Create Entity",
                                input_pins=[{"name": "scene", "type": "any"}],
                                output_pins=[{"name": "entity", "type": "any"}],
                                default_properties={"name": "Entity", "position": [0, 0, 0]})

        self.register_node_type("npc_create", "Game", "Create NPC",
                                input_pins=[{"name": "scene", "type": "any"}],
                                output_pins=[{"name": "npc", "type": "any"}],
                                default_properties={"name": "NPC", "personality": {}})
