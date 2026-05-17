"""
SparkLabs Agent - Shader Advisor Engine

AI-driven shader selection, generation, and performance analysis system
for real-time rendering pipelines. Maintains a library of shader presets
across domains and techniques, provides natural-language-to-shader
generation, scene-based recommendations, and compile-time validation.

Architecture:
  ShaderAdvisor
    |-- ShaderPreset (reusable shader template with code and metadata)
    |-- Preset Library (organized by domain, language, technique)
    |-- AI Generator (natural language description to shader code)
    |-- Scene Recommender (context-aware shader suggestions)
    |-- Performance Analyzer (score-based shader evaluation)
    |-- Compile Checker (syntax validation against target language)
    |-- Preset Exporter (serialize preset to portable format)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ShaderDomain(Enum):
    SURFACE = "surface"
    POST_PROCESS = "post_process"
    PARTICLE = "particle"
    SKY = "sky"
    WATER = "water"
    UI = "ui"
    COMPUTE = "compute"


class ShaderLanguage(Enum):
    GLSL = "glsl"
    HLSL = "hlsl"
    WGSL = "wgsl"
    METAL = "metal"


class ShaderTechnique(Enum):
    PHONG = "phong"
    PBR = "pbr"
    TOON = "toon"
    UNLIT = "unlit"
    VOLUMETRIC = "volumetric"
    PARALLAX = "parallax"
    SUBSUFACE = "subsurface"


DOMAIN_KEYWORDS: Dict[ShaderDomain, List[str]] = {
    ShaderDomain.SURFACE: ["surface", "material", "object", "mesh", "model", "fresnel"],
    ShaderDomain.POST_PROCESS: ["post process", "bloom", "tone mapping", "color grading", "ssao", "motion blur", "depth"],
    ShaderDomain.PARTICLE: ["particle", "spark", "smoke", "fire", "explosion", "trail", "ribbon"],
    ShaderDomain.SKY: ["sky", "atmosphere", "cloud", "star", "celestial", "horizon", "sun", "moon"],
    ShaderDomain.WATER: ["water", "ocean", "river", "lake", "reflection", "refraction", "wave", "foam", "caustics"],
    ShaderDomain.UI: ["ui", "interface", "hud", "text", "icon", "panel", "button", "progress"],
    ShaderDomain.COMPUTE: ["compute", "gpu", "parallel", "simulation", "particle system", "fourier", "ocean fft"],
}

TECHNIQUE_DESCRIPTIONS: Dict[ShaderTechnique, str] = {
    ShaderTechnique.PHONG: "Classic per-pixel lighting with ambient, diffuse, and specular components.",
    ShaderTechnique.PBR: "Physically based rendering with metallic-roughness workflow and image-based lighting.",
    ShaderTechnique.TOON: "Cel-shaded rendering with stepped lighting bands and outline edges.",
    ShaderTechnique.UNLIT: "Flat color or texture output with no lighting calculations.",
    ShaderTechnique.VOLUMETRIC: "Ray-marched volumetric effects for fog, clouds, and light scattering.",
    ShaderTechnique.PARALLAX: "Parallax occlusion mapping for depth-enhanced surface detail.",
    ShaderTechnique.SUBSUFACE: "Subsurface scattering simulation for skin, wax, and organic materials.",
}

LANGUAGE_EXTENSIONS: Dict[ShaderLanguage, str] = {
    ShaderLanguage.GLSL: ".glsl",
    ShaderLanguage.HLSL: ".hlsl",
    ShaderLanguage.WGSL: ".wgsl",
    ShaderLanguage.METAL: ".metal",
}


@dataclass
class ShaderPreset:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    domain: ShaderDomain = ShaderDomain.SURFACE
    language: ShaderLanguage = ShaderLanguage.GLSL
    technique: ShaderTechnique = ShaderTechnique.PBR
    vertex_code: str = ""
    fragment_code: str = ""
    uniforms: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    performance_score: float = 100.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "language": self.language.value,
            "technique": self.technique.value,
            "vertex_code": self.vertex_code,
            "fragment_code": self.fragment_code,
            "uniforms": self.uniforms,
            "tags": self.tags,
            "performance_score": self.performance_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ShaderAdvisor:
    """AI-powered shader selection, generation, and performance analysis engine."""

    _instance: Optional["ShaderAdvisor"] = None
    _lock = threading.RLock()

    MAX_PRESETS = 500

    def __init__(self):
        self._presets: Dict[str, ShaderPreset] = {}
        self._total_presets: int = 0
        self._generation_count: int = 0
        self._recommendation_count: int = 0
        self._analysis_count: int = 0
        self._seed_presets()

    @classmethod
    def get_instance(cls) -> "ShaderAdvisor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed_presets(self) -> None:
        seed_data = [
            {
                "name": "Standard PBR Surface",
                "domain": ShaderDomain.SURFACE,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.PBR,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 1) in vec3 aNormal;\n"
                    "layout(location = 2) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec3 vWorldPos;\n"
                    "layout(location = 1) out vec3 vNormal;\n"
                    "layout(location = 2) out vec2 vTexCoord;\n"
                    "uniform mat4 uModel;\n"
                    "uniform mat4 uViewProjection;\n"
                    "void main() {\n"
                    "    vec4 worldPos = uModel * vec4(aPosition, 1.0);\n"
                    "    vWorldPos = worldPos.xyz;\n"
                    "    vNormal = mat3(uModel) * aNormal;\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    gl_Position = uViewProjection * worldPos;\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vWorldPos;\n"
                    "layout(location = 1) in vec3 vNormal;\n"
                    "layout(location = 2) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uAlbedoMap;\n"
                    "uniform sampler2D uNormalMap;\n"
                    "uniform sampler2D uMetallicRoughnessMap;\n"
                    "uniform vec3 uLightDir;\n"
                    "uniform vec3 uViewPos;\n"
                    "void main() {\n"
                    "    vec3 albedo = texture(uAlbedoMap, vTexCoord).rgb;\n"
                    "    vec3 N = normalize(vNormal);\n"
                    "    vec3 V = normalize(uViewPos - vWorldPos);\n"
                    "    vec3 L = normalize(uLightDir);\n"
                    "    vec3 H = normalize(L + V);\n"
                    "    float NdotL = max(dot(N, L), 0.0);\n"
                    "    float NdotH = max(dot(N, H), 0.0);\n"
                    "    vec3 diffuse = albedo * NdotL;\n"
                    "    vec3 specular = vec3(0.04) * pow(NdotH, 64.0);\n"
                    "    fragColor = vec4(diffuse + specular, 1.0);\n"
                    "}\n"
                ),
                "uniforms": {
                    "uAlbedoMap": "sampler2D",
                    "uNormalMap": "sampler2D",
                    "uMetallicRoughnessMap": "sampler2D",
                    "uLightDir": "vec3",
                    "uViewPos": "vec3",
                    "uModel": "mat4",
                    "uViewProjection": "mat4",
                },
                "tags": ["pbr", "surface", "lighting", "standard"],
                "performance_score": 85.0,
            },
            {
                "name": "Toon Shading",
                "domain": ShaderDomain.SURFACE,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.TOON,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 1) in vec3 aNormal;\n"
                    "layout(location = 0) out vec3 vNormal;\n"
                    "layout(location = 1) out vec3 vWorldPos;\n"
                    "uniform mat4 uModel;\n"
                    "uniform mat4 uViewProjection;\n"
                    "void main() {\n"
                    "    vec4 worldPos = uModel * vec4(aPosition, 1.0);\n"
                    "    vWorldPos = worldPos.xyz;\n"
                    "    vNormal = mat3(uModel) * aNormal;\n"
                    "    gl_Position = uViewProjection * worldPos;\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vNormal;\n"
                    "layout(location = 1) in vec3 vWorldPos;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform vec3 uLightDir;\n"
                    "uniform vec3 uBaseColor;\n"
                    "uniform float uBandCount;\n"
                    "void main() {\n"
                    "    vec3 N = normalize(vNormal);\n"
                    "    vec3 L = normalize(uLightDir);\n"
                    "    float NdotL = dot(N, L) * 0.5 + 0.5;\n"
                    "    float band = floor(NdotL * uBandCount) / uBandCount;\n"
                    "    fragColor = vec4(uBaseColor * band, 1.0);\n"
                    "}\n"
                ),
                "uniforms": {
                    "uModel": "mat4",
                    "uViewProjection": "mat4",
                    "uLightDir": "vec3",
                    "uBaseColor": "vec3",
                    "uBandCount": "float",
                },
                "tags": ["toon", "cel", "stylized", "anime"],
                "performance_score": 92.0,
            },
            {
                "name": "Unlit Texture",
                "domain": ShaderDomain.UI,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.UNLIT,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec2 aPosition;\n"
                    "layout(location = 1) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec2 vTexCoord;\n"
                    "void main() {\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    gl_Position = vec4(aPosition, 0.0, 1.0);\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uTexture;\n"
                    "uniform vec4 uTintColor;\n"
                    "void main() {\n"
                    "    fragColor = texture(uTexture, vTexCoord) * uTintColor;\n"
                    "}\n"
                ),
                "uniforms": {
                    "uTexture": "sampler2D",
                    "uTintColor": "vec4",
                },
                "tags": ["ui", "unlit", "sprite", "gui"],
                "performance_score": 98.0,
            },
            {
                "name": "Particle Billboard",
                "domain": ShaderDomain.PARTICLE,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.UNLIT,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 1) in vec2 aTexCoord;\n"
                    "layout(location = 2) in vec4 aColor;\n"
                    "layout(location = 0) out vec2 vTexCoord;\n"
                    "layout(location = 1) out vec4 vColor;\n"
                    "uniform mat4 uViewProjection;\n"
                    "uniform vec3 uCameraRight;\n"
                    "uniform vec3 uCameraUp;\n"
                    "uniform vec3 uParticleCenter;\n"
                    "uniform float uSize;\n"
                    "void main() {\n"
                    "    vec3 pos = uParticleCenter;\n"
                    "    pos += uCameraRight * aPosition.x * uSize;\n"
                    "    pos += uCameraUp * aPosition.y * uSize;\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    vColor = aColor;\n"
                    "    gl_Position = uViewProjection * vec4(pos, 1.0);\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec2 vTexCoord;\n"
                    "layout(location = 1) in vec4 vColor;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uParticleTexture;\n"
                    "void main() {\n"
                    "    vec4 texColor = texture(uParticleTexture, vTexCoord);\n"
                    "    fragColor = texColor * vColor;\n"
                    "    if (fragColor.a < 0.01) discard;\n"
                    "}\n"
                ),
                "uniforms": {
                    "uViewProjection": "mat4",
                    "uCameraRight": "vec3",
                    "uCameraUp": "vec3",
                    "uParticleCenter": "vec3",
                    "uSize": "float",
                    "uParticleTexture": "sampler2D",
                },
                "tags": ["particle", "billboard", "vfx", "alpha"],
                "performance_score": 88.0,
            },
            {
                "name": "Sky Atmosphere",
                "domain": ShaderDomain.SKY,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.VOLUMETRIC,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 0) out vec3 vDirection;\n"
                    "uniform mat4 uInverseViewProjection;\n"
                    "void main() {\n"
                    "    vec4 clipPos = vec4(aPosition.xy, 0.0, 1.0);\n"
                    "    vec4 worldDir = uInverseViewProjection * clipPos;\n"
                    "    vDirection = normalize(worldDir.xyz / worldDir.w);\n"
                    "    gl_Position = clipPos;\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vDirection;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform vec3 uSunDirection;\n"
                    "uniform float uAtmosphereDensity;\n"
                    "void main() {\n"
                    "    vec3 dir = normalize(vDirection);\n"
                    "    float sunAngle = max(dot(dir, normalize(uSunDirection)), 0.0);\n"
                    "    vec3 skyColor = mix(vec3(0.5, 0.7, 1.0), vec3(1.0, 0.9, 0.7), sunAngle * uAtmosphereDensity);\n"
                    "    skyColor += vec3(1.0, 0.6, 0.2) * pow(sunAngle, 32.0) * 0.3;\n"
                    "    fragColor = vec4(skyColor, 1.0);\n"
                    "}\n"
                ),
                "uniforms": {
                    "uInverseViewProjection": "mat4",
                    "uSunDirection": "vec3",
                    "uAtmosphereDensity": "float",
                },
                "tags": ["sky", "atmosphere", "sun", "volumetric"],
                "performance_score": 78.0,
            },
            {
                "name": "Water Surface with Fresnel",
                "domain": ShaderDomain.WATER,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.PHONG,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 1) in vec3 aNormal;\n"
                    "layout(location = 2) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec3 vWorldPos;\n"
                    "layout(location = 1) out vec3 vNormal;\n"
                    "layout(location = 2) out vec2 vTexCoord;\n"
                    "uniform mat4 uModel;\n"
                    "uniform mat4 uViewProjection;\n"
                    "void main() {\n"
                    "    vec4 worldPos = uModel * vec4(aPosition, 1.0);\n"
                    "    vWorldPos = worldPos.xyz;\n"
                    "    vNormal = mat3(uModel) * aNormal;\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    gl_Position = uViewProjection * worldPos;\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vWorldPos;\n"
                    "layout(location = 1) in vec3 vNormal;\n"
                    "layout(location = 2) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uWaveNormalMap;\n"
                    "uniform samplerCube uEnvironmentMap;\n"
                    "uniform vec3 uViewPos;\n"
                    "uniform float uTime;\n"
                    "void main() {\n"
                    "    vec3 N = normalize(vNormal);\n"
                    "    vec3 V = normalize(uViewPos - vWorldPos);\n"
                    "    float fresnel = pow(1.0 - abs(dot(N, V)), 3.0);\n"
                    "    vec3 reflectDir = reflect(-V, N);\n"
                    "    vec3 envColor = texture(uEnvironmentMap, reflectDir).rgb;\n"
                    "    vec3 waterColor = mix(vec3(0.1, 0.3, 0.6), envColor, fresnel);\n"
                    "    fragColor = vec4(waterColor, 0.85);\n"
                    "}\n"
                ),
                "uniforms": {
                    "uModel": "mat4",
                    "uViewProjection": "mat4",
                    "uWaveNormalMap": "sampler2D",
                    "uEnvironmentMap": "samplerCube",
                    "uViewPos": "vec3",
                    "uTime": "float",
                },
                "tags": ["water", "fresnel", "reflection", "environment"],
                "performance_score": 72.0,
            },
            {
                "name": "Bloom Post Process",
                "domain": ShaderDomain.POST_PROCESS,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.UNLIT,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec2 aPosition;\n"
                    "layout(location = 1) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec2 vTexCoord;\n"
                    "void main() {\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    gl_Position = vec4(aPosition, 0.0, 1.0);\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uSceneColor;\n"
                    "uniform sampler2D uBloomTexture;\n"
                    "uniform float uBloomIntensity;\n"
                    "void main() {\n"
                    "    vec3 scene = texture(uSceneColor, vTexCoord).rgb;\n"
                    "    vec3 bloom = texture(uBloomTexture, vTexCoord).rgb;\n"
                    "    fragColor = vec4(scene + bloom * uBloomIntensity, 1.0);\n"
                    "}\n"
                ),
                "uniforms": {
                    "uSceneColor": "sampler2D",
                    "uBloomTexture": "sampler2D",
                    "uBloomIntensity": "float",
                },
                "tags": ["post_process", "bloom", "composite", "hdr"],
                "performance_score": 75.0,
            },
            {
                "name": "Parallax Occlusion Surface",
                "domain": ShaderDomain.SURFACE,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.PARALLAX,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 1) in vec3 aNormal;\n"
                    "layout(location = 2) in vec3 aTangent;\n"
                    "layout(location = 3) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec3 vWorldPos;\n"
                    "layout(location = 1) out vec3 vNormal;\n"
                    "layout(location = 2) out vec3 vTangent;\n"
                    "layout(location = 3) out vec2 vTexCoord;\n"
                    "layout(location = 4) out vec3 vViewDirTS;\n"
                    "uniform mat4 uModel;\n"
                    "uniform mat4 uViewProjection;\n"
                    "uniform vec3 uViewPos;\n"
                    "void main() {\n"
                    "    vec4 worldPos = uModel * vec4(aPosition, 1.0);\n"
                    "    vWorldPos = worldPos.xyz;\n"
                    "    vNormal = mat3(uModel) * aNormal;\n"
                    "    vTangent = mat3(uModel) * aTangent;\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    vec3 N = normalize(vNormal);\n"
                    "    vec3 T = normalize(vTangent);\n"
                    "    vec3 B = cross(N, T);\n"
                    "    mat3 TBN = transpose(mat3(T, B, N));\n"
                    "    vViewDirTS = TBN * normalize(uViewPos - vWorldPos);\n"
                    "    gl_Position = uViewProjection * worldPos;\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vWorldPos;\n"
                    "layout(location = 1) in vec3 vNormal;\n"
                    "layout(location = 2) in vec3 vTangent;\n"
                    "layout(location = 3) in vec2 vTexCoord;\n"
                    "layout(location = 4) in vec3 vViewDirTS;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uHeightMap;\n"
                    "uniform sampler2D uAlbedoMap;\n"
                    "uniform float uParallaxScale;\n"
                    "uniform float uParallaxLayers;\n"
                    "void main() {\n"
                    "    vec3 V = normalize(vViewDirTS);\n"
                    "    float layerDepth = 1.0 / uParallaxLayers;\n"
                    "    float currentDepth = 0.0;\n"
                    "    vec2 delta = V.xy * uParallaxScale / (V.z * uParallaxLayers);\n"
                    "    vec2 currentUV = vTexCoord;\n"
                    "    float height = 1.0 - texture(uHeightMap, currentUV).r;\n"
                    "    for (int i = 0; i < 32; i++) {\n"
                    "        if (currentDepth >= height) break;\n"
                    "        currentUV -= delta;\n"
                    "        height = 1.0 - texture(uHeightMap, currentUV).r;\n"
                    "        currentDepth += layerDepth;\n"
                    "    }\n"
                    "    fragColor = texture(uAlbedoMap, currentUV);\n"
                    "}\n"
                ),
                "uniforms": {
                    "uModel": "mat4",
                    "uViewProjection": "mat4",
                    "uViewPos": "vec3",
                    "uHeightMap": "sampler2D",
                    "uAlbedoMap": "sampler2D",
                    "uParallaxScale": "float",
                    "uParallaxLayers": "float",
                },
                "tags": ["parallax", "occlusion", "height", "displacement"],
                "performance_score": 60.0,
            },
            {
                "name": "GPU Particle Simulation",
                "domain": ShaderDomain.COMPUTE,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.UNLIT,
                "vertex_code": "",
                "fragment_code": (
                    "#version 450\n"
                    "layout(local_size_x = 256, local_size_y = 1, local_size_z = 1) in;\n"
                    "layout(std430, binding = 0) buffer ParticleBuffer {\n"
                    "    vec4 positions[];\n"
                    "    vec4 velocities[];\n"
                    "    float lifetimes[];\n"
                    "} particles;\n"
                    "uniform float uDeltaTime;\n"
                    "uniform float uGravity;\n"
                    "uniform uint uParticleCount;\n"
                    "void main() {\n"
                    "    uint idx = gl_GlobalInvocationID.x;\n"
                    "    if (idx >= uParticleCount) return;\n"
                    "    vec4 vel = particles.velocities[idx];\n"
                    "    vel.y -= uGravity * uDeltaTime;\n"
                    "    particles.positions[idx] += vel * uDeltaTime;\n"
                    "    particles.lifetimes[idx] -= uDeltaTime;\n"
                    "}\n"
                ),
                "uniforms": {
                    "uDeltaTime": "float",
                    "uGravity": "float",
                    "uParticleCount": "uint",
                },
                "tags": ["compute", "gpu", "particle", "simulation"],
                "performance_score": 70.0,
            },
            {
                "name": "Subsurface Scattering Skin",
                "domain": ShaderDomain.SURFACE,
                "language": ShaderLanguage.GLSL,
                "technique": ShaderTechnique.SUBSUFACE,
                "vertex_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 1) in vec3 aNormal;\n"
                    "layout(location = 2) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec3 vWorldPos;\n"
                    "layout(location = 1) out vec3 vNormal;\n"
                    "layout(location = 2) out vec2 vTexCoord;\n"
                    "uniform mat4 uModel;\n"
                    "uniform mat4 uViewProjection;\n"
                    "void main() {\n"
                    "    vec4 worldPos = uModel * vec4(aPosition, 1.0);\n"
                    "    vWorldPos = worldPos.xyz;\n"
                    "    vNormal = mat3(uModel) * aNormal;\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    gl_Position = uViewProjection * worldPos;\n"
                    "}\n"
                ),
                "fragment_code": (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vWorldPos;\n"
                    "layout(location = 1) in vec3 vNormal;\n"
                    "layout(location = 2) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uAlbedoMap;\n"
                    "uniform sampler2D uThicknessMap;\n"
                    "uniform vec3 uLightDir;\n"
                    "uniform vec3 uViewPos;\n"
                    "uniform vec3 uScatterColor;\n"
                    "uniform float uScatterRadius;\n"
                    "void main() {\n"
                    "    vec3 albedo = texture(uAlbedoMap, vTexCoord).rgb;\n"
                    "    float thickness = texture(uThicknessMap, vTexCoord).r;\n"
                    "    vec3 N = normalize(vNormal);\n"
                    "    vec3 V = normalize(uViewPos - vWorldPos);\n"
                    "    vec3 L = normalize(uLightDir);\n"
                    "    float NdotL = max(dot(N, L), 0.0);\n"
                    "    vec3 sss = uScatterColor * thickness * (1.0 - NdotL) * uScatterRadius;\n"
                    "    vec3 diffuse = albedo * NdotL;\n"
                    "    fragColor = vec4(diffuse + sss, 1.0);\n"
                    "}\n"
                ),
                "uniforms": {
                    "uModel": "mat4",
                    "uViewProjection": "mat4",
                    "uAlbedoMap": "sampler2D",
                    "uThicknessMap": "sampler2D",
                    "uLightDir": "vec3",
                    "uViewPos": "vec3",
                    "uScatterColor": "vec3",
                    "uScatterRadius": "float",
                },
                "tags": ["subsurface", "skin", "scattering", "organic"],
                "performance_score": 55.0,
            },
        ]

        for data in seed_data:
            preset = ShaderPreset(**data)
            self._presets[preset.id] = preset
            self._total_presets += 1

    def create_preset(
        self,
        name: str,
        domain: str = "surface",
        language: str = "glsl",
        technique: str = "pbr",
        vertex_code: str = "",
        fragment_code: str = "",
        uniforms: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        performance_score: float = 100.0,
    ) -> ShaderPreset:
        preset = ShaderPreset(
            name=name,
            domain=ShaderDomain(domain),
            language=ShaderLanguage(language),
            technique=ShaderTechnique(technique),
            vertex_code=vertex_code,
            fragment_code=fragment_code,
            uniforms=uniforms or {},
            tags=tags or [],
            performance_score=performance_score,
        )
        self._presets[preset.id] = preset
        self._total_presets += 1

        if len(self._presets) > self.MAX_PRESETS:
            oldest = min(self._presets.values(), key=lambda p: p.created_at)
            del self._presets[oldest.id]

        return preset

    def generate_from_description(
        self,
        description: str,
        language: str = "glsl",
    ) -> ShaderPreset:
        desc_lower = description.lower()

        domain = ShaderDomain.SURFACE
        for d, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                domain = d
                break

        technique = ShaderTechnique.PBR
        for t in ShaderTechnique:
            technique_keywords: Dict[ShaderTechnique, List[str]] = {
                ShaderTechnique.PHONG: ["phong", "blinn", "classic lighting"],
                ShaderTechnique.PBR: ["pbr", "physically based", "realistic", "metallic"],
                ShaderTechnique.TOON: ["toon", "cel", "cartoon", "anime", "stylized", "cell shaded"],
                ShaderTechnique.UNLIT: ["unlit", "flat", "no lighting", "ui", "sprite", "text"],
                ShaderTechnique.VOLUMETRIC: ["volumetric", "ray march", "fog", "cloud", "volume"],
                ShaderTechnique.PARALLAX: ["parallax", "occlusion", "displacement", "height map"],
                ShaderTechnique.SUBSUFACE: ["subsurface", "sss", "skin", "scatter", "scattering", "wax", "organic"],
            }
            for t_key, t_kws in technique_keywords.items():
                if any(kw in desc_lower for kw in t_kws):
                    technique = t_key
                    break

        lang = ShaderLanguage(language) if language in [l.value for l in ShaderLanguage] else ShaderLanguage.GLSL
        name = f"Generated {technique.value.upper()} Shader"

        vertex_code = ""
        fragment_code = ""
        uniforms: Dict[str, str] = {}

        if technique in (ShaderTechnique.UNLIT,):
            if domain == ShaderDomain.UI:
                vertex_code = (
                    "#version 450\n"
                    "layout(location = 0) in vec2 aPosition;\n"
                    "layout(location = 1) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec2 vTexCoord;\n"
                    "void main() {\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    gl_Position = vec4(aPosition, 0.0, 1.0);\n"
                    "}\n"
                )
                fragment_code = (
                    "#version 450\n"
                    "layout(location = 0) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uTexture;\n"
                    "void main() {\n"
                    "    fragColor = texture(uTexture, vTexCoord);\n"
                    "}\n"
                )
                uniforms = {"uTexture": "sampler2D"}
            else:
                vertex_code = (
                    "#version 450\n"
                    "layout(location = 0) in vec3 aPosition;\n"
                    "layout(location = 1) in vec2 aTexCoord;\n"
                    "layout(location = 0) out vec2 vTexCoord;\n"
                    "uniform mat4 uViewProjection;\n"
                    "uniform mat4 uModel;\n"
                    "void main() {\n"
                    "    vTexCoord = aTexCoord;\n"
                    "    gl_Position = uViewProjection * uModel * vec4(aPosition, 1.0);\n"
                    "}\n"
                )
                fragment_code = (
                    "#version 450\n"
                    "layout(location = 0) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uAlbedo;\n"
                    "void main() {\n"
                    "    fragColor = texture(uAlbedo, vTexCoord);\n"
                    "}\n"
                )
                uniforms = {
                    "uViewProjection": "mat4",
                    "uModel": "mat4",
                    "uAlbedo": "sampler2D",
                }
        else:
            vertex_code = (
                "#version 450\n"
                "layout(location = 0) in vec3 aPosition;\n"
                "layout(location = 1) in vec3 aNormal;\n"
                "layout(location = 2) in vec2 aTexCoord;\n"
                "layout(location = 0) out vec3 vWorldPos;\n"
                "layout(location = 1) out vec3 vNormal;\n"
                "layout(location = 2) out vec2 vTexCoord;\n"
                "uniform mat4 uModel;\n"
                "uniform mat4 uViewProjection;\n"
                "void main() {\n"
                "    vec4 worldPos = uModel * vec4(aPosition, 1.0);\n"
                "    vWorldPos = worldPos.xyz;\n"
                "    vNormal = mat3(uModel) * aNormal;\n"
                "    vTexCoord = aTexCoord;\n"
                "    gl_Position = uViewProjection * worldPos;\n"
                "}\n"
            )
            uniforms = {
                "uModel": "mat4",
                "uViewProjection": "mat4",
                "uAlbedoMap": "sampler2D",
                "uLightDir": "vec3",
                "uViewPos": "vec3",
            }

            if technique == ShaderTechnique.TOON:
                fragment_code = (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vNormal;\n"
                    "layout(location = 1) in vec3 vWorldPos;\n"
                    "layout(location = 2) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uAlbedoMap;\n"
                    "uniform vec3 uLightDir;\n"
                    "uniform vec3 uViewPos;\n"
                    "uniform float uSteps;\n"
                    "void main() {\n"
                    "    vec3 N = normalize(vNormal);\n"
                    "    vec3 L = normalize(uLightDir);\n"
                    "    float diffuse = max(dot(N, L), 0.0);\n"
                    "    float stepped = floor(diffuse * uSteps) / uSteps;\n"
                    "    vec3 albedo = texture(uAlbedoMap, vTexCoord).rgb;\n"
                    "    fragColor = vec4(albedo * stepped + vec3(0.05), 1.0);\n"
                    "}\n"
                )
                uniforms["uSteps"] = "float"
            else:
                fragment_code = (
                    "#version 450\n"
                    "layout(location = 0) in vec3 vWorldPos;\n"
                    "layout(location = 1) in vec3 vNormal;\n"
                    "layout(location = 2) in vec2 vTexCoord;\n"
                    "layout(location = 0) out vec4 fragColor;\n"
                    "uniform sampler2D uAlbedoMap;\n"
                    "uniform vec3 uLightDir;\n"
                    "uniform vec3 uViewPos;\n"
                    "void main() {\n"
                    "    vec3 N = normalize(vNormal);\n"
                    "    vec3 V = normalize(uViewPos - vWorldPos);\n"
                    "    vec3 L = normalize(uLightDir);\n"
                    "    vec3 albedo = texture(uAlbedoMap, vTexCoord).rgb;\n"
                    "    float NdotL = max(dot(N, L), 0.0);\n"
                    "    vec3 diffuse = albedo * NdotL;\n"
                    "    vec3 ambient = albedo * 0.1;\n"
                    "    fragColor = vec4(diffuse + ambient, 1.0);\n"
                    "}\n"
                )

        tags = list({kw for kw_list in DOMAIN_KEYWORDS.values() for kw in kw_list if kw in desc_lower})
        tags.insert(0, technique.value)

        preset = ShaderPreset(
            name=name,
            domain=domain,
            language=lang,
            technique=technique,
            vertex_code=vertex_code,
            fragment_code=fragment_code,
            uniforms=uniforms,
            tags=tags[:10],
            performance_score=100.0,
        )
        self._presets[preset.id] = preset
        self._total_presets += 1
        self._generation_count += 1

        if len(self._presets) > self.MAX_PRESETS:
            oldest = min(self._presets.values(), key=lambda p: p.created_at)
            del self._presets[oldest.id]

        return preset

    def get_presets_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        try:
            d = ShaderDomain(domain)
        except ValueError:
            return []
        return [p.to_dict() for p in self._presets.values() if p.domain == d]

    def get_presets_by_technique(self, technique: str) -> List[Dict[str, Any]]:
        try:
            t = ShaderTechnique(technique)
        except ValueError:
            return []
        return [p.to_dict() for p in self._presets.values() if p.technique == t]

    def recommend_for_scene(
        self,
        scene_description: str,
        max_results: int = 3,
    ) -> List[Dict[str, Any]]:
        desc_lower = scene_description.lower()

        target_domain: Optional[ShaderDomain] = None
        target_technique: Optional[ShaderTechnique] = None

        for d, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                target_domain = d
                break

        for t in ShaderTechnique:
            tech_keywords: Dict[ShaderTechnique, List[str]] = {
                ShaderTechnique.PHONG: ["phong", "blinn", "classic lighting"],
                ShaderTechnique.PBR: ["pbr", "physically based", "realistic", "metallic"],
                ShaderTechnique.TOON: ["toon", "cel", "cartoon", "anime", "stylized"],
                ShaderTechnique.UNLIT: ["unlit", "flat", "no lighting", "ui", "sprite"],
                ShaderTechnique.VOLUMETRIC: ["volumetric", "ray march", "fog", "cloud", "volume"],
                ShaderTechnique.PARALLAX: ["parallax", "occlusion", "displacement"],
                ShaderTechnique.SUBSUFACE: ["subsurface", "sss", "skin", "scatter", "wax", "organic"],
            }
            for t_key, t_kws in tech_keywords.items():
                if any(kw in desc_lower for kw in t_kws):
                    target_technique = t_key
                    break
            if target_technique:
                break

        scored: List[tuple[ShaderPreset, float]] = []
        for preset in self._presets.values():
            score = 0.0
            if target_domain and preset.domain == target_domain:
                score += 5.0
            if target_technique and preset.technique == target_technique:
                score += 4.0
            tag_match = sum(1 for tag in preset.tags if tag in desc_lower)
            score += tag_match * 2.0
            score += preset.performance_score / 100.0
            if score > 0:
                scored.append((preset, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = scored[:max_results]
        self._recommendation_count += 1
        return [p.to_dict() for p, _ in results]

    def analyze_performance(self, preset_id: str) -> Dict[str, Any]:
        preset = self._presets.get(preset_id)
        if preset is None:
            return {"error": f"Preset '{preset_id}' not found"}

        score = preset.performance_score
        if score >= 90:
            rating = "excellent"
            notes = "Minimal GPU cost, suitable for low-end devices and large draw-call counts."
        elif score >= 75:
            rating = "good"
            notes = "Moderate GPU usage. Acceptable for most scenes with reasonable draw-call budgets."
        elif score >= 60:
            rating = "fair"
            notes = "Above-average GPU demand. Consider culling distant objects using this shader."
        elif score >= 40:
            rating = "poor"
            notes = "High GPU cost. Use sparingly and only for hero objects with limited instances."
        else:
            rating = "critical"
            notes = "Extremely expensive. Restrict to cinematic close-ups or precompute alternatives offline."

        code_lines = preset.vertex_code.count("\n") + preset.fragment_code.count("\n")
        uniform_count = len(preset.uniforms)
        texture_slots = sum(1 for u in preset.uniforms.values() if "sampler" in u)
        complexity = "low" if uniform_count <= 3 else ("medium" if uniform_count <= 7 else "high")

        self._analysis_count += 1
        return {
            "preset_id": preset_id,
            "preset_name": preset.name,
            "domain": preset.domain.value,
            "technique": preset.technique.value,
            "performance_score": score,
            "performance_rating": rating,
            "analysis_notes": notes,
            "code_lines": code_lines,
            "uniform_count": uniform_count,
            "texture_slots": texture_slots,
            "shader_complexity": complexity,
            "analyzed_at": time.time(),
        }

    def compile_check(self, preset_id: str) -> Dict[str, Any]:
        preset = self._presets.get(preset_id)
        if preset is None:
            return {"error": f"Preset '{preset_id}' not found"}

        issues: List[str] = []

        if not preset.vertex_code.strip():
            issues.append("Missing vertex shader code.")
        if not preset.fragment_code.strip():
            issues.append("Missing fragment shader code.")

        for uniform_name, uniform_type in preset.uniforms.items():
            if uniform_type not in ("int", "uint", "float", "bool", "vec2", "vec3", "vec4",
                                      "mat3", "mat4", "sampler2D", "samplerCube", "sampler2DArray",
                                      "sampler3D", "ivec2", "ivec3", "ivec4"):
                issues.append(f"Uniform '{uniform_name}' has unrecognized type '{uniform_type}'.")

        version_found = "#version" in preset.vertex_code or "#version" in preset.fragment_code
        gl_position_found = "gl_Position" in preset.vertex_code
        frag_output_found = "fragColor" in preset.fragment_code or "out vec4" in preset.fragment_code

        if not version_found:
            issues.append("No #version directive found in shader code.")
        if not gl_position_found and preset.vertex_code:
            issues.append("Vertex shader may not write to gl_Position.")
        if not frag_output_found and preset.fragment_code:
            issues.append("Fragment shader may not declare an output variable.")

        turns = [
            {"type": "syntax_check", "errors": len(issues), "warnings": 0},
        ]

        pass_count = len([t for t in turns if t["errors"] == 0])
        fail_count = len(turns) - pass_count
        status = "passed" if fail_count == 0 else "warning"

        return {
            "preset_id": preset_id,
            "preset_name": preset.name,
            "language": preset.language.value,
            "compile_status": status,
            "checks_passed": pass_count,
            "checks_failed": fail_count,
            "issues": issues,
            "compile_turns": turns,
            "checked_at": time.time(),
        }

    def export_preset(
        self,
        preset_id: str,
        target_language: Optional[str] = None,
    ) -> Dict[str, Any]:
        preset = self._presets.get(preset_id)
        if preset is None:
            return {"error": f"Preset '{preset_id}' not found"}

        lang = ShaderLanguage(target_language) if target_language else preset.language
        extension = LANGUAGE_EXTENSIONS.get(lang, ".glsl")

        export_vertex = preset.vertex_code
        export_fragment = preset.fragment_code

        prefix = "// Auto-generated by ShaderAdvisor\n"
        prefix += f"// Preset: {preset.name}\n"
        prefix += f"// Domain: {preset.domain.value} | Technique: {preset.technique.value}\n"
        prefix += f"// Language: {lang.value} | Performance Score: {preset.performance_score:.0f}\n"
        prefix += f"// Uniforms: {', '.join(preset.uniforms.keys())}\n\n"

        return {
            "preset_id": preset_id,
            "preset_name": preset.name,
            "source_language": preset.language.value,
            "target_language": lang.value,
            "file_extension": extension,
            "vertex_source": prefix + export_vertex,
            "fragment_source": prefix + export_fragment,
            "uniforms": preset.uniforms,
            "metadata": {
                "domain": preset.domain.value,
                "technique": preset.technique.value,
                "tags": preset.tags,
                "performance_score": preset.performance_score,
            },
            "exported_at": time.time(),
        }

    def get_stats(self) -> Dict[str, Any]:
        domain_counts: Dict[str, int] = {}
        technique_counts: Dict[str, int] = {}
        language_counts: Dict[str, int] = {}

        total_score: float = 0.0
        for preset in self._presets.values():
            domain_counts[preset.domain.value] = domain_counts.get(preset.domain.value, 0) + 1
            technique_counts[preset.technique.value] = technique_counts.get(preset.technique.value, 0) + 1
            language_counts[preset.language.value] = language_counts.get(preset.language.value, 0) + 1
            total_score += preset.performance_score

        avg_score = total_score / len(self._presets) if self._presets else 0.0

        return {
            "total_presets": len(self._presets),
            "total_presets_created": self._total_presets,
            "generation_count": self._generation_count,
            "recommendation_count": self._recommendation_count,
            "analysis_count": self._analysis_count,
            "average_performance_score": round(avg_score, 1),
            "by_domain": domain_counts,
            "by_technique": technique_counts,
            "by_language": language_counts,
            "max_presets": self.MAX_PRESETS,
        }


def get_shader_advisor() -> ShaderAdvisor:
    return ShaderAdvisor.get_instance()