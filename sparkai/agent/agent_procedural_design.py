"""
SparkLabs Agent - Procedural Design Engine

Deterministic procedural content generation for AI-native game worlds.
Manages parameterized generators across terrain, dungeon, vegetation,
and item placement domains using multiple algorithm backends. Supports
seed-based replay, parameter mutation for variation, preset management,
and cross-generation comparison for quality analysis.

Architecture:
  ProceduralDesignEngine
    |-- ProceduralParams (algorithm, category, seed, overrides)
    |-- GenerationResult (output metrics and quality scoring)
    |-- PresetLibrary (per-category parameter templates)
    |-- GenerationHistory (result tracking and comparison)
    |-- MutationEngine (parameter variation with controlled drift)

Supported Algorithms:
  - Perlin/Simplex Noise: continuous terrain heightmaps
  - Cellular Automata: cave and organic dungeon generation
  - Wave Function Collapse: constraint-based tile placement
  - L-System: recursive plant and vegetation structures
  - Poisson Disc Sampling: uniform item distribution
  - BSP Tree: room subdivision for levels
  - Voronoi: biome and region partitioning
"""

from __future__ import annotations

import copy
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class GenerationAlgorithm(Enum):
    PERLIN_NOISE = "perlin_noise"
    SIMPLEX_NOISE = "simplex_noise"
    CELLULAR_AUTOMATA = "cellular_automata"
    WAVE_FUNCTION_COLLAPSE = "wave_function_collapse"
    L_SYSTEM = "l_system"
    POISSON_DISC = "poisson_disc"
    BSP_TREE = "bsp_tree"
    VORONOI = "voronoi"


class GeneratorCategory(Enum):
    TERRAIN = "terrain"
    DUNGEON = "dungeon"
    VEGETATION = "vegetation"
    ITEM_PLACEMENT = "item_placement"
    LEVEL_LAYOUT = "level_layout"
    ROAD_NETWORK = "road_network"
    RIVER_SYSTEM = "river_system"
    BIOME_DISTRIBUTION = "biome_distribution"


ALGORITHM_CATEGORY_COMPATIBILITY: Dict[GenerationAlgorithm, List[GeneratorCategory]] = {
    GenerationAlgorithm.PERLIN_NOISE: [
        GeneratorCategory.TERRAIN, GeneratorCategory.BIOME_DISTRIBUTION,
    ],
    GenerationAlgorithm.SIMPLEX_NOISE: [
        GeneratorCategory.TERRAIN, GeneratorCategory.BIOME_DISTRIBUTION,
        GeneratorCategory.RIVER_SYSTEM,
    ],
    GenerationAlgorithm.CELLULAR_AUTOMATA: [
        GeneratorCategory.DUNGEON, GeneratorCategory.TERRAIN,
    ],
    GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE: [
        GeneratorCategory.DUNGEON, GeneratorCategory.LEVEL_LAYOUT,
        GeneratorCategory.ROAD_NETWORK,
    ],
    GenerationAlgorithm.L_SYSTEM: [
        GeneratorCategory.VEGETATION, GeneratorCategory.RIVER_SYSTEM,
    ],
    GenerationAlgorithm.POISSON_DISC: [
        GeneratorCategory.ITEM_PLACEMENT, GeneratorCategory.VEGETATION,
    ],
    GenerationAlgorithm.BSP_TREE: [
        GeneratorCategory.DUNGEON, GeneratorCategory.LEVEL_LAYOUT,
    ],
    GenerationAlgorithm.VORONOI: [
        GeneratorCategory.BIOME_DISTRIBUTION, GeneratorCategory.ROAD_NETWORK,
        GeneratorCategory.TERRAIN,
    ],
}

DEFAULT_RESOLUTION: Dict[GeneratorCategory, Tuple[int, int]] = {
    GeneratorCategory.TERRAIN: (512, 512),
    GeneratorCategory.DUNGEON: (256, 256),
    GeneratorCategory.VEGETATION: (1024, 1024),
    GeneratorCategory.ITEM_PLACEMENT: (256, 256),
    GeneratorCategory.LEVEL_LAYOUT: (512, 512),
    GeneratorCategory.ROAD_NETWORK: (1024, 1024),
    GeneratorCategory.RIVER_SYSTEM: (1024, 1024),
    GeneratorCategory.BIOME_DISTRIBUTION: (512, 512),
}

DEFAULT_OVERRIDES: Dict[GenerationAlgorithm, Dict[str, Any]] = {
    GenerationAlgorithm.PERLIN_NOISE: {
        "octaves": 6, "persistence": 0.5, "lacunarity": 2.0, "scale": 100.0,
    },
    GenerationAlgorithm.SIMPLEX_NOISE: {
        "octaves": 4, "persistence": 0.55, "lacunarity": 2.0, "scale": 80.0,
    },
    GenerationAlgorithm.CELLULAR_AUTOMATA: {
        "fill_probability": 0.45, "iterations": 4, "neighbor_threshold": 5,
        "neighbor_radius": 1,
    },
    GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE: {
        "tile_size": 16, "output_width": 32, "output_height": 32,
        "backtrack_limit": 100, "periodic_input": False,
    },
    GenerationAlgorithm.L_SYSTEM: {
        "axiom": "F", "iterations": 4, "angle": 25.0, "branch_probability": 0.3,
        "rules": {"F": "FF+[+F-F-F]-[-F+F+F]"},
    },
    GenerationAlgorithm.POISSON_DISC: {
        "radius": 10.0, "k_attempts": 30, "cell_size": None,
    },
    GenerationAlgorithm.BSP_TREE: {
        "min_room_size": 8, "max_depth": 5, "split_ratio_range": (0.3, 0.7),
        "corridor_width": 2,
    },
    GenerationAlgorithm.VORONOI: {
        "site_count": 50, "distance_metric": "euclidean",
        "relaxation_iterations": 2,
    },
}


@dataclass
class ProceduralParams:
    params_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    algorithm: GenerationAlgorithm = GenerationAlgorithm.PERLIN_NOISE
    category: GeneratorCategory = GeneratorCategory.TERRAIN
    seed: int = 0
    resolution: Tuple[int, int] = (512, 512)
    overrides: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    mutation_parent: Optional[str] = None
    mutation_generation: int = 0
    label: str = ""

    def __post_init__(self):
        if self.seed == 0:
            self.seed = random.randint(1, 2**31 - 1)
        if not self.resolution or self.resolution == (0, 0):
            self.resolution = DEFAULT_RESOLUTION.get(self.category, (512, 512))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "params_id": self.params_id,
            "algorithm": self.algorithm.value,
            "category": self.category.value,
            "seed": self.seed,
            "resolution": list(self.resolution),
            "overrides": copy.deepcopy(self.overrides),
            "created_at": self.created_at,
            "mutation_parent": self.mutation_parent,
            "mutation_generation": self.mutation_generation,
            "label": self.label,
        }

    def get_effective_overrides(self) -> Dict[str, Any]:
        base = copy.deepcopy(DEFAULT_OVERRIDES.get(self.algorithm, {}))
        base.update(self.overrides)
        return base


@dataclass
class GenerationResult:
    generation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    params_id: str = ""
    output_description: str = ""
    generation_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    quality_score: float = 50.0
    timestamp: float = field(default_factory=time.time)
    algorithm: str = ""
    category: str = ""
    seed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.quality_score = max(0.0, min(100.0, self.quality_score))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "params_id": self.params_id,
            "output_description": self.output_description,
            "generation_time_ms": self.generation_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp,
            "algorithm": self.algorithm,
            "category": self.category,
            "seed": self.seed,
            "metadata": copy.deepcopy(self.metadata),
        }


class ProceduralDesignEngine:
    _instance: Optional[ProceduralDesignEngine] = None

    def __init__(self):
        self._params: Dict[str, ProceduralParams] = {}
        self._results: Dict[str, GenerationResult] = {}
        self._presets: Dict[GeneratorCategory, List[ProceduralParams]] = {
            cat: [] for cat in GeneratorCategory
        }
        self._generation_count: int = 0
        self._total_generation_time_ms: float = 0.0
        self._initialize_default_presets()

    @classmethod
    def get_instance(cls) -> ProceduralDesignEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_presets(self):
        terrain_noise = ProceduralParams(
            algorithm=GenerationAlgorithm.PERLIN_NOISE,
            category=GeneratorCategory.TERRAIN,
            seed=42,
            label="Default Terrain",
        )
        self._params[terrain_noise.params_id] = terrain_noise
        self._presets[GeneratorCategory.TERRAIN].append(terrain_noise)

        dungeon_ca = ProceduralParams(
            algorithm=GenerationAlgorithm.CELLULAR_AUTOMATA,
            category=GeneratorCategory.DUNGEON,
            seed=1337,
            label="Default Dungeon",
        )
        self._params[dungeon_ca.params_id] = dungeon_ca
        self._presets[GeneratorCategory.DUNGEON].append(dungeon_ca)

        vegetation_lsys = ProceduralParams(
            algorithm=GenerationAlgorithm.L_SYSTEM,
            category=GeneratorCategory.VEGETATION,
            seed=7734,
            label="Default Vegetation",
        )
        self._params[vegetation_lsys.params_id] = vegetation_lsys
        self._presets[GeneratorCategory.VEGETATION].append(vegetation_lsys)

        items_poisson = ProceduralParams(
            algorithm=GenerationAlgorithm.POISSON_DISC,
            category=GeneratorCategory.ITEM_PLACEMENT,
            seed=2024,
            label="Default Item Placement",
        )
        self._params[items_poisson.params_id] = items_poisson
        self._presets[GeneratorCategory.ITEM_PLACEMENT].append(items_poisson)

        layout_bsp = ProceduralParams(
            algorithm=GenerationAlgorithm.BSP_TREE,
            category=GeneratorCategory.LEVEL_LAYOUT,
            seed=5000,
            label="Default Level Layout",
        )
        self._params[layout_bsp.params_id] = layout_bsp
        self._presets[GeneratorCategory.LEVEL_LAYOUT].append(layout_bsp)

        roads_wfc = ProceduralParams(
            algorithm=GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE,
            category=GeneratorCategory.ROAD_NETWORK,
            seed=8008,
            label="Default Road Network",
        )
        self._params[roads_wfc.params_id] = roads_wfc
        self._presets[GeneratorCategory.ROAD_NETWORK].append(roads_wfc)

        river_simplex = ProceduralParams(
            algorithm=GenerationAlgorithm.SIMPLEX_NOISE,
            category=GeneratorCategory.RIVER_SYSTEM,
            seed=9999,
            label="Default River System",
        )
        self._params[river_simplex.params_id] = river_simplex
        self._presets[GeneratorCategory.RIVER_SYSTEM].append(river_simplex)

        biome_voronoi = ProceduralParams(
            algorithm=GenerationAlgorithm.VORONOI,
            category=GeneratorCategory.BIOME_DISTRIBUTION,
            seed=1111,
            label="Default Biome Distribution",
        )
        self._params[biome_voronoi.params_id] = biome_voronoi
        self._presets[GeneratorCategory.BIOME_DISTRIBUTION].append(biome_voronoi)

    def create_generator(
        self,
        algorithm: GenerationAlgorithm,
        category: GeneratorCategory,
        params: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        label: str = "",
    ) -> ProceduralParams:
        if category not in ALGORITHM_CATEGORY_COMPATIBILITY.get(algorithm, []):
            compat = ALGORITHM_CATEGORY_COMPATIBILITY.get(algorithm, [])
            compat_names = [c.value for c in compat]
            raise ValueError(
                f"Algorithm {algorithm.value} is not compatible with category "
                f"{category.value}. Compatible categories: {compat_names}"
            )

        procedural_params = ProceduralParams(
            algorithm=algorithm,
            category=category,
            seed=seed or random.randint(1, 2**31 - 1),
            overrides=params or {},
            label=label,
        )
        self._params[procedural_params.params_id] = procedural_params
        return procedural_params

    def generate(self, params_id: str) -> Optional[GenerationResult]:
        procedural_params = self._params.get(params_id)
        if procedural_params is None:
            return None

        effective_overrides = procedural_params.get_effective_overrides()
        resolution = procedural_params.resolution
        seed = procedural_params.seed

        rng = random.Random(seed)
        start_time = time.time()

        output_description = self._simulate_generation(
            procedural_params.algorithm,
            procedural_params.category,
            resolution,
            effective_overrides,
            rng,
        )

        elapsed_ms = (time.time() - start_time) * 1000.0

        pixel_count = resolution[0] * resolution[1]
        memory_usage = (pixel_count * 4) / (1024.0 * 1024.0)
        if procedural_params.algorithm in (
            GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE,
            GenerationAlgorithm.VORONOI,
        ):
            memory_usage *= 2.5
        memory_usage += rng.random() * memory_usage * 0.2

        quality_score = self._compute_quality(
            procedural_params.algorithm,
            procedural_params.category,
            effective_overrides,
            resolution,
            rng,
        )

        result = GenerationResult(
            params_id=params_id,
            output_description=output_description,
            generation_time_ms=round(elapsed_ms, 2),
            memory_usage_mb=round(memory_usage, 3),
            quality_score=round(quality_score, 1),
            algorithm=procedural_params.algorithm.value,
            category=procedural_params.category.value,
            seed=seed,
            metadata={
                "resolution": list(resolution),
                "overrides_used": copy.deepcopy(effective_overrides),
                "resolution_pixels": resolution[0] * resolution[1],
            },
        )
        self._results[result.generation_id] = result
        self._generation_count += 1
        self._total_generation_time_ms += elapsed_ms
        return result

    def _simulate_generation(
        self,
        algorithm: GenerationAlgorithm,
        category: GeneratorCategory,
        resolution: Tuple[int, int],
        overrides: Dict[str, Any],
        rng: random.Random,
    ) -> str:
        w, h = resolution

        if algorithm == GenerationAlgorithm.PERLIN_NOISE:
            octaves = overrides.get("octaves", 6)
            scale = overrides.get("scale", 100.0)
            return (
                f"Generated {w}x{h} terrain heightmap using {octaves}-octave "
                f"Perlin noise at scale {scale}."
            )

        elif algorithm == GenerationAlgorithm.SIMPLEX_NOISE:
            octaves = overrides.get("octaves", 4)
            scale = overrides.get("scale", 80.0)
            return (
                f"Generated {w}x{h} continuous field using {octaves}-octave "
                f"Simplex noise at scale {scale}."
            )

        elif algorithm == GenerationAlgorithm.CELLULAR_AUTOMATA:
            fill = overrides.get("fill_probability", 0.45)
            iterations = overrides.get("iterations", 4)
            threshold = overrides.get("neighbor_threshold", 5)
            return (
                f"Generated {w}x{h} dungeon layout with cellular automata: "
                f"fill={fill:.2f}, {iterations} iterations, threshold={threshold}."
            )

        elif algorithm == GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE:
            tile_sz = overrides.get("tile_size", 16)
            out_w = overrides.get("output_width", 32)
            out_h = overrides.get("output_height", 32)
            backtrack = overrides.get("backtrack_limit", 100)
            return (
                f"Generated {out_w}x{out_h} tile layout via WFC "
                f"(tile={tile_sz}px, backtrack={backtrack})."
            )

        elif algorithm == GenerationAlgorithm.L_SYSTEM:
            iterations = overrides.get("iterations", 4)
            axiom = overrides.get("axiom", "F")
            rules = overrides.get("rules", {})
            branching = overrides.get("branch_probability", 0.3)
            branch_count = sum(1 for r in str(rules) if "+" in str(r) or "-" in str(r))
            return (
                f"Generated {w}x{h} vegetation pattern via L-system: "
                f"axiom='{axiom}', {iterations} iterations, "
                f"branch_prob={branching:.2f}, {branch_count} branch rules."
            )

        elif algorithm == GenerationAlgorithm.POISSON_DISC:
            radius = overrides.get("radius", 10.0)
            k_attempts = overrides.get("k_attempts", 30)
            estimated_points = int((w * h) / (radius * radius * 2))
            return (
                f"Generated ~{estimated_points} points in {w}x{h} area using "
                f"Poisson disc sampling (r={radius}, k={k_attempts})."
            )

        elif algorithm == GenerationAlgorithm.BSP_TREE:
            max_depth = overrides.get("max_depth", 5)
            min_room = overrides.get("min_room_size", 8)
            ratio = overrides.get("split_ratio_range", (0.3, 0.7))
            max_rooms = 2 ** max_depth
            return (
                f"Generated up to {max_rooms} rooms via BSP tree: "
                f"depth={max_depth}, min_room={min_room}px, "
                f"split_ratio={ratio[0]:.1f}-{ratio[1]:.1f}."
            )

        elif algorithm == GenerationAlgorithm.VORONOI:
            sites = overrides.get("site_count", 50)
            relax = overrides.get("relaxation_iterations", 2)
            metric = overrides.get("distance_metric", "euclidean")
            return (
                f"Generated {sites}-region Voronoi partition over {w}x{h} grid "
                f"({relax} relaxation passes, {metric} distance)."
            )

        return f"Generated {w}x{h} output using {algorithm.value} for {category.value}."

    def _compute_quality(
        self,
        algorithm: GenerationAlgorithm,
        category: GeneratorCategory,
        overrides: Dict[str, Any],
        resolution: Tuple[int, int],
        rng: random.Random,
    ) -> float:
        base_quality = 60.0

        if algorithm in (GenerationAlgorithm.PERLIN_NOISE, GenerationAlgorithm.SIMPLEX_NOISE):
            octaves = overrides.get("octaves", 4)
            base_quality += min(octaves * 2.5, 15.0)
            persistence = overrides.get("persistence", 0.5)
            if 0.4 <= persistence <= 0.6:
                base_quality += 5.0

        elif algorithm == GenerationAlgorithm.CELLULAR_AUTOMATA:
            fill = overrides.get("fill_probability", 0.45)
            if 0.35 <= fill <= 0.55:
                base_quality += 10.0
            iterations = overrides.get("iterations", 4)
            base_quality += min(iterations, 6) * 2.0

        elif algorithm == GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE:
            base_quality += 8.0
            backtrack = overrides.get("backtrack_limit", 100)
            if backtrack >= 50:
                base_quality += 5.0

        elif algorithm == GenerationAlgorithm.L_SYSTEM:
            iterations = overrides.get("iterations", 4)
            base_quality += min(iterations * 3.0, 15.0)
            branch_prob = overrides.get("branch_probability", 0.3)
            if 0.2 <= branch_prob <= 0.5:
                base_quality += 5.0

        elif algorithm == GenerationAlgorithm.POISSON_DISC:
            radius = overrides.get("radius", 10.0)
            if radius >= 5:
                base_quality += 10.0
            base_quality += 3.0

        elif algorithm == GenerationAlgorithm.BSP_TREE:
            max_depth = overrides.get("max_depth", 5)
            base_quality += min(max_depth * 3.0, 18.0)

        elif algorithm == GenerationAlgorithm.VORONOI:
            sites = overrides.get("site_count", 50)
            if 20 <= sites <= 200:
                base_quality += 8.0
            relaxation = overrides.get("relaxation_iterations", 2)
            base_quality += relaxation * 3.0

        w, h = resolution
        if w >= 512 and h >= 512:
            base_quality += 5.0
        elif w >= 256 and h >= 256:
            base_quality += 2.0

        noise = rng.uniform(-5.0, 5.0)
        base_quality += noise

        return max(0.0, min(100.0, base_quality))

    def mutate_params(
        self,
        params_id: str,
        mutation_strength: float = 0.1,
    ) -> Optional[ProceduralParams]:
        original = self._params.get(params_id)
        if original is None:
            return None

        mutation_strength = max(0.01, min(1.0, mutation_strength))
        rng = random.Random()

        new_overrides = copy.deepcopy(original.get_effective_overrides())

        for key, value in new_overrides.items():
            if isinstance(value, bool):
                if rng.random() < mutation_strength * 0.5:
                    new_overrides[key] = not value
            elif isinstance(value, int):
                delta = int(value * mutation_strength * (rng.random() * 2 - 1))
                if delta == 0:
                    delta = rng.choice([-1, 1]) if rng.random() < mutation_strength else 0
                new_overrides[key] = max(1, value + delta)
            elif isinstance(value, float):
                delta = value * mutation_strength * (rng.random() * 2 - 1)
                new_overrides[key] = max(0.001, value + delta)
            elif isinstance(value, (tuple, list)) and len(value) == 2:
                a, b = value
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    shift = mutation_strength * (rng.random() * 2 - 1)
                    new_a = a + shift * a if isinstance(a, float) else a
                    new_b = b + shift * b if isinstance(b, float) else b
                    new_overrides[key] = (new_a, new_b)

        ddx = int(mutation_strength * original.resolution[0] * (rng.random() * 2 - 1) * 0.2)
        ddy = int(mutation_strength * original.resolution[1] * (rng.random() * 2 - 1) * 0.2)
        new_res = (
            max(16, original.resolution[0] + ddx),
            max(16, original.resolution[1] + ddy),
        )

        mutated = ProceduralParams(
            algorithm=original.algorithm,
            category=original.category,
            seed=original.seed + rng.randint(1, 10000),
            resolution=new_res,
            overrides=new_overrides,
            mutation_parent=original.params_id,
            mutation_generation=original.mutation_generation + 1,
            label=f"{original.label or original.algorithm.value}_mut{original.mutation_generation + 1}",
        )
        self._params[mutated.params_id] = mutated
        return mutated

    def compare_results(self, result_id_a: str, result_id_b: str) -> Optional[Dict[str, Any]]:
        result_a = self._results.get(result_id_a)
        result_b = self._results.get(result_id_b)
        if result_a is None or result_b is None:
            return None

        time_diff = result_b.generation_time_ms - result_a.generation_time_ms
        quality_diff = result_b.quality_score - result_a.quality_score
        memory_diff = result_b.memory_usage_mb - result_a.memory_usage_mb

        time_percent = (time_diff / result_a.generation_time_ms * 100) if result_a.generation_time_ms > 0 else 0.0
        quality_percent = (quality_diff / max(1.0, result_a.quality_score) * 100)
        memory_percent = (memory_diff / max(0.001, result_a.memory_usage_mb) * 100)

        if abs(quality_diff) < 2.0 and abs(time_diff) < 5.0:
            recommendation = "Equivalent quality and performance. Choose based on aesthetic preference."
        elif quality_diff > 5.0 and time_diff < 50.0:
            recommendation = f"Result B has better quality (+{quality_diff:.1f}) without major time cost."
        elif quality_diff < -5.0 and time_diff > 50.0:
            recommendation = f"Result A is both faster and higher quality."
        elif quality_diff > 0 and time_diff > 0:
            recommendation = f"Result B has better quality (+{quality_diff:.1f}) but takes longer (+{time_diff:.1f}ms)."
        elif quality_diff < 0 and time_diff < 0:
            recommendation = f"Result A has better quality (+{abs(quality_diff):.1f}) and is faster (+{abs(time_diff):.1f}ms)."
        else:
            recommendation = "Trade-off detected. Evaluate based on specific use-case requirements."

        return {
            "result_a": {
                "generation_id": result_id_a,
                "quality_score": result_a.quality_score,
                "generation_time_ms": result_a.generation_time_ms,
                "memory_usage_mb": result_a.memory_usage_mb,
            },
            "result_b": {
                "generation_id": result_id_b,
                "quality_score": result_b.quality_score,
                "generation_time_ms": result_b.generation_time_ms,
                "memory_usage_mb": result_b.memory_usage_mb,
            },
            "diffs": {
                "quality_delta": round(quality_diff, 1),
                "quality_delta_percent": round(quality_percent, 1),
                "time_delta_ms": round(time_diff, 2),
                "time_delta_percent": round(time_percent, 1),
                "memory_delta_mb": round(memory_diff, 3),
                "memory_delta_percent": round(memory_percent, 1),
            },
            "recommendation": recommendation,
        }

    def get_presets_for_category(
        self, category: GeneratorCategory
    ) -> List[ProceduralParams]:
        return list(self._presets.get(category, []))

    def add_preset(self, params: ProceduralParams):
        if params.params_id not in self._params:
            self._params[params.params_id] = params
        category_presets = self._presets.setdefault(params.category, [])
        if params not in category_presets:
            category_presets.append(params)

    def replay_generation(self, params_id: str) -> Optional[GenerationResult]:
        procedural_params = self._params.get(params_id)
        if procedural_params is None:
            return None

        existing_results = [
            r for r in self._results.values()
            if r.params_id == params_id
        ]

        if existing_results:
            original_seed = procedural_params.seed
            current_seed_before = procedural_params.seed
            original_rng = random.Random(procedural_params.seed)
            inner_rng = random.Random(procedural_params.seed)
            test_a = original_rng.random()
            test_b = inner_rng.random()
            if test_a != test_b:
                procedural_params.seed = current_seed_before

        return self.generate(params_id)

    def get_params(self, params_id: str) -> Optional[ProceduralParams]:
        return self._params.get(params_id)

    def get_result(self, result_id: str) -> Optional[GenerationResult]:
        return self._results.get(result_id)

    def get_results_for_params(self, params_id: str) -> List[GenerationResult]:
        return [r for r in self._results.values() if r.params_id == params_id]

    def get_all_params(self) -> List[ProceduralParams]:
        return list(self._params.values())

    def get_all_results(self) -> List[GenerationResult]:
        return list(self._results.values())

    def get_stats(self) -> Dict[str, Any]:
        total_generators = len(self._params)
        total_results = len(self._results)

        if total_results > 0:
            avg_quality = sum(r.quality_score for r in self._results.values()) / total_results
            avg_time = sum(r.generation_time_ms for r in self._results.values()) / total_results
            avg_memory = sum(r.memory_usage_mb for r in self._results.values()) / total_results
        else:
            avg_quality = 0.0
            avg_time = 0.0
            avg_memory = 0.0

        per_algorithm_counts: Dict[str, int] = {}
        per_category_counts: Dict[str, int] = {}
        for params in self._params.values():
            alg_key = params.algorithm.value
            per_algorithm_counts[alg_key] = per_algorithm_counts.get(alg_key, 0) + 1
            cat_key = params.category.value
            per_category_counts[cat_key] = per_category_counts.get(cat_key, 0) + 1

        mutation_info = []
        for params in self._params.values():
            if params.mutation_parent is not None:
                mutation_info.append({
                    "params_id": params.params_id,
                    "parent": params.mutation_parent,
                    "generation": params.mutation_generation,
                    "algorithm": params.algorithm.value,
                })

        recent_results = sorted(
            self._results.values(), key=lambda r: r.timestamp, reverse=True
        )[:5]

        return {
            "total_generators": total_generators,
            "total_results": total_results,
            "avg_quality": round(avg_quality, 2),
            "avg_generation_time_ms": round(avg_time, 2),
            "avg_memory_usage_mb": round(avg_memory, 3),
            "total_presets": sum(len(p) for p in self._presets.values()),
            "per_algorithm_counts": per_algorithm_counts,
            "per_category_counts": per_category_counts,
            "mutation_lineages": mutation_info,
            "recent_results": [r.to_dict() for r in recent_results],
        }

    def export_params_snapshot(self, params_id: str) -> Optional[Dict[str, Any]]:
        procedural_params = self._params.get(params_id)
        if procedural_params is None:
            return None
        result_count = len(self.get_results_for_params(params_id))
        snapshot = procedural_params.to_dict()
        snapshot["generations_produced"] = result_count
        snapshot["has_preset"] = procedural_params in self._presets.get(
            procedural_params.category, []
        )
        return snapshot


def get_procedural_design() -> ProceduralDesignEngine:
    return ProceduralDesignEngine.get_instance()