"""
SparkLabs Engine - Shader System

2D shader and material management system for visual effects
in AI-generated games. Manages shader compilation, uniform
parameters, material instances, and render passes — enabling
post-processing, sprite effects, and dynamic lighting.

Architecture:
  ShaderSystem
    |-- ShaderProgram (vertex + fragment source with compilation)
    |-- UniformBlock (typed uniform parameters with dirty tracking)
    |-- Material (shader + uniform values = renderable appearance)
    |-- RenderPass (ordered pass list for compositing pipeline)

Built-in Shaders:
  - default_sprite: standard textured quad rendering
  - outline: silhouette edge detection and rendering
  - glow: bloom/gaussian blur post-processing
  - dissolve: noise-based alpha dithering transition
  - palette_swap: index-based color replacement

Usage:
    ss = ShaderSystem()
    outline = ss.compile("outline", {"thickness": 2.0, "color": [1, 0, 0, 1]})
    mat = ss.create_material("enemy_material", "outline", outline.uniforms)
    ss.apply_material("enemy_sprite", "enemy_material")
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class UniformType(Enum):
    FLOAT = auto()
    VEC2 = auto()
    VEC3 = auto()
    VEC4 = auto()
    INT = auto()
    BOOL = auto()
    SAMPLER2D = auto()
    MATRIX4 = auto()


@dataclass
class UniformParameter:
    name: str = ""
    uniform_type: UniformType = UniformType.FLOAT
    default_value: Any = 0.0
    current_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    dirty: bool = True

    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.default_value

    def set(self, value: Any) -> None:
        if value != self.current_value:
            self.current_value = value
            self.dirty = True

    def mark_clean(self) -> None:
        self.dirty = False


@dataclass
class ShaderProgram:
    program_id: str = ""
    name: str = ""
    vertex_source: str = ""
    fragment_source: str = ""
    uniforms: Dict[str, UniformParameter] = field(default_factory=dict)
    compiled: bool = False
    compile_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set_uniform(self, name: str, value: Any) -> bool:
        if name in self.uniforms:
            self.uniforms[name].set(value)
            return True
        return False

    def get_uniform(self, name: str) -> Optional[Any]:
        param = self.uniforms.get(name)
        return param.current_value if param else None

    def mark_all_clean(self) -> None:
        for param in self.uniforms.values():
            param.mark_clean()

    def has_dirty_uniforms(self) -> bool:
        return any(p.dirty for p in self.uniforms.values())


class BlendMode(Enum):
    OPAQUE = auto()
    ALPHA = auto()
    ADDITIVE = auto()
    MULTIPLY = auto()
    SCREEN = auto()


class CullMode(Enum):
    NONE = auto()
    FRONT = auto()
    BACK = auto()


@dataclass
class RenderState:
    blend_mode: BlendMode = BlendMode.ALPHA
    cull_mode: CullMode = CullMode.NONE
    depth_test: bool = False
    depth_write: bool = False
    wireframe: bool = False
    line_width: float = 1.0
    stencil_enabled: bool = False


@dataclass
class Material:
    material_id: str = ""
    name: str = ""
    shader_id: str = ""
    uniforms: Dict[str, Any] = field(default_factory=dict)
    render_state: RenderState = field(default_factory=RenderState)
    render_queue: int = 2000
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderPass:
    pass_id: str = ""
    name: str = ""
    target: str = "screen"
    clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    clear_depth: bool = True
    enable_post_processing: bool = True
    order: int = 0
    enabled: bool = True


BUILTIN_SHADERS: Dict[str, Dict[str, Any]] = {
    "default_sprite": {
        "uniforms": {
            "mainTexture": (UniformType.SAMPLER2D, None, "Primary texture sampler"),
            "colorTint": (UniformType.VEC4, (1.0, 1.0, 1.0, 1.0), "Color multiplier"),
            "alphaCutoff": (UniformType.FLOAT, 0.0, "Alpha threshold for discard"),
        },
    },
    "outline": {
        "uniforms": {
            "thickness": (UniformType.FLOAT, 1.0, "Outline width in pixels"),
            "color": (UniformType.VEC4, (1.0, 0.0, 0.0, 1.0), "Outline color"),
        },
    },
    "glow": {
        "uniforms": {
            "intensity": (UniformType.FLOAT, 1.0, "Glow brightness multiplier"),
            "radius": (UniformType.FLOAT, 4.0, "Blur radius in pixels"),
            "color": (UniformType.VEC4, (1.0, 1.0, 1.0, 1.0), "Glow tint color"),
        },
    },
    "dissolve": {
        "uniforms": {
            "progress": (UniformType.FLOAT, 0.0, "Dissolve progress 0-1"),
            "noiseScale": (UniformType.FLOAT, 10.0, "Noise pattern scale"),
            "edgeWidth": (UniformType.FLOAT, 0.05, "Burn edge width"),
            "edgeColor": (UniformType.VEC4, (1.0, 0.5, 0.0, 1.0), "Burn edge glow color"),
        },
    },
    "palette_swap": {
        "uniforms": {
            "paletteTexture": (UniformType.SAMPLER2D, None, "Color lookup palette"),
            "swapIndex": (UniformType.INT, 0, "Palette row to use"),
        },
    },
}


class ShaderSystem:
    _instance: Optional["ShaderSystem"] = None

    def __init__(self):
        self._shaders: Dict[str, ShaderProgram] = {}
        self._materials: Dict[str, Material] = {}
        self._render_passes: Dict[str, RenderPass] = {}
        self._material_assignments: Dict[str, str] = {}
        self._compilation_count: int = 0

    @classmethod
    def get_instance(cls) -> "ShaderSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def compile(self, shader_name: str, initial_uniforms: Optional[Dict[str, Any]] = None) -> ShaderProgram:
        start = time.monotonic()

        if shader_name in BUILTIN_SHADERS:
            template = BUILTIN_SHADERS[shader_name]
            uniforms: Dict[str, UniformParameter] = {}
            for u_name, (u_type, u_default, u_desc) in template["uniforms"].items():
                uniforms[u_name] = UniformParameter(
                    name=u_name,
                    uniform_type=u_type,
                    default_value=u_default if u_default is not None else 0.0,
                    description=u_desc,
                )

            program = ShaderProgram(
                program_id=str(uuid.uuid4())[:8],
                name=shader_name,
                vertex_source=f"// vertex for {shader_name}",
                fragment_source=f"// fragment for {shader_name}",
                uniforms=uniforms,
                compiled=True,
                compile_time_ms=(time.monotonic() - start) * 1000,
            )
        else:
            program = ShaderProgram(
                program_id=str(uuid.uuid4())[:8],
                name=shader_name,
                compiled=True,
                compile_time_ms=(time.monotonic() - start) * 1000,
            )

        if initial_uniforms:
            for name, value in initial_uniforms.items():
                program.set_uniform(name, value)

        self._shaders[program.program_id] = program
        self._compilation_count += 1
        return program

    def get_shader(self, program_id: str) -> Optional[ShaderProgram]:
        return self._shaders.get(program_id)

    def find_shader(self, name: str) -> Optional[ShaderProgram]:
        for shader in self._shaders.values():
            if shader.name == name:
                return shader
        return None

    def create_material(
        self,
        name: str,
        shader_id_or_name: str,
        uniforms: Optional[Dict[str, Any]] = None,
        render_queue: int = 2000,
    ) -> Material:
        shader = self._shaders.get(shader_id_or_name)
        if not shader:
            shader = self.find_shader(shader_id_or_name)
        if not shader:
            shader = self.compile(shader_id_or_name)

        mat = Material(
            material_id=str(uuid.uuid4())[:8],
            name=name,
            shader_id=shader.program_id,
            uniforms=uniforms or {},
            render_queue=render_queue,
        )
        self._materials[mat.material_id] = mat
        return mat

    def get_material(self, material_id: str) -> Optional[Material]:
        return self._materials.get(material_id)

    def apply_material(self, target_id: str, material_id: str) -> bool:
        if material_id in self._materials:
            self._material_assignments[target_id] = material_id
            return True
        return False

    def remove_material_assignment(self, target_id: str) -> bool:
        return self._material_assignments.pop(target_id, None) is not None

    def get_assigned_material(self, target_id: str) -> Optional[Material]:
        material_id = self._material_assignments.get(target_id)
        return self._materials.get(material_id) if material_id else None

    def add_render_pass(
        self,
        name: str,
        target: str = "screen",
        order: int = 0,
        **kwargs,
    ) -> RenderPass:
        rp = RenderPass(
            pass_id=str(uuid.uuid4())[:8],
            name=name,
            target=target,
            order=order,
            **kwargs,
        )
        self._render_passes[rp.pass_id] = rp
        return rp

    def get_sorted_passes(self) -> List[RenderPass]:
        passes = list(self._render_passes.values())
        passes.sort(key=lambda p: p.order)
        return passes

    def set_sprite_uniform(
        self, target_id: str, uniform_name: str, value: Any
    ) -> bool:
        material = self.get_assigned_material(target_id)
        if not material:
            return False
        material.uniforms[uniform_name] = value

        shader = self._shaders.get(material.shader_id)
        if shader:
            shader.set_uniform(uniform_name, value)
        return True

    def list_shaders(self) -> List[Dict[str, Any]]:
        return [
            {
                "program_id": s.program_id, "name": s.name,
                "compiled": s.compiled, "uniform_count": len(s.uniforms),
                "available": list(s.uniforms.keys()),
            }
            for s in self._shaders.values()
        ]

    def list_materials(self) -> List[Dict[str, Any]]:
        return [
            {
                "material_id": m.material_id, "name": m.name,
                "shader_id": m.shader_id, "enabled": m.enabled,
                "render_queue": m.render_queue,
            }
            for m in self._materials.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "shader_count": len(self._shaders),
            "material_count": len(self._materials),
            "render_pass_count": len(self._render_passes),
            "active_material_assignments": len(self._material_assignments),
            "compilation_count": self._compilation_count,
            "available_shaders": list(BUILTIN_SHADERS.keys()),
        }


def get_shader_system() -> ShaderSystem:
    return ShaderSystem.get_instance()
