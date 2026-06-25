"""
SparkAI Physics Optimizer Engine - Advanced physics simulation optimization.

Provides intelligent physics optimization including adaptive timestep
control, collision detection optimization, spatial partitioning strategies,
and constraint solver tuning for optimal physics performance.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PhysicsSolverType(Enum):
    """Available physics solver types."""
    PROJECTED_GAUSS_SEIDEL = "projected_gauss_seidel"
    SEQUENTIAL_IMPULSE = "sequential_impulse"
    TEMPORAL_GAUSS_SEIDEL = "temporal_gauss_seidel"
    NONLINEAR_GAUSS_SEIDEL = "nonlinear_gauss_seidel"


class SpatialStrategy(Enum):
    """Spatial partitioning strategies for broad-phase collision."""
    GRID_HASH = "grid_hash"
    BOUNDING_VOLUME_HIERARCHY = "bounding_volume_hierarchy"
    SWEEP_AND_PRUNE = "sweep_and_prune"
    KD_TREE = "kd_tree"
    QUAD_TREE = "quad_tree"
    OCTREE = "octree"
    ADAPTIVE_GRID = "adaptive_grid"


class OptimizationTarget(Enum):
    """Targets for physics optimization."""
    COLLISION_PERFORMANCE = "collision_performance"
    CONSTRAINT_SOLVING = "constraint_solving"
    BROAD_PHASE = "broad_phase"
    NARROW_PHASE = "narrow_phase"
    INTEGRATION = "integration"
    SLEEP_MANAGEMENT = "sleep_management"
    ISLAND_MANAGEMENT = "island_management"


class PhysicsQualityLevel(Enum):
    """Quality levels for physics simulation."""
    PRECISION = "precision"
    HIGH = "high"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    MINIMAL = "minimal"


@dataclass
class PhysicsProfile:
    """Performance profile for physics simulation."""
    profile_id: str
    body_count: int = 0
    active_body_count: int = 0
    sleeping_body_count: int = 0
    collision_pair_count: int = 0
    contact_count: int = 0
    constraint_count: int = 0
    island_count: int = 0
    broad_phase_time_ms: float = 0.0
    narrow_phase_time_ms: float = 0.0
    solver_time_ms: float = 0.0
    integration_time_ms: float = 0.0
    total_physics_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "body_count": self.body_count,
            "active_body_count": self.active_body_count,
            "sleeping_body_count": self.sleeping_body_count,
            "collision_pair_count": self.collision_pair_count,
            "contact_count": self.contact_count,
            "constraint_count": self.constraint_count,
            "island_count": self.island_count,
            "broad_phase_time_ms": self.broad_phase_time_ms,
            "narrow_phase_time_ms": self.narrow_phase_time_ms,
            "solver_time_ms": self.solver_time_ms,
            "integration_time_ms": self.integration_time_ms,
            "total_physics_time_ms": self.total_physics_time_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class PhysicsConfiguration:
    """Current physics engine configuration."""
    solver_type: PhysicsSolverType = PhysicsSolverType.SEQUENTIAL_IMPULSE
    spatial_strategy: SpatialStrategy = SpatialStrategy.BOUNDING_VOLUME_HIERARCHY
    quality_level: PhysicsQualityLevel = PhysicsQualityLevel.BALANCED
    fixed_timestep: float = 0.016667  # 60 Hz
    max_sub_steps: int = 4
    velocity_iterations: int = 8
    position_iterations: int = 3
    enable_sleeping: bool = True
    sleep_linear_threshold: float = 0.01
    sleep_angular_threshold: float = 0.01
    sleep_time_threshold: float = 0.5
    enable_continuous_collision: bool = True
    gravity: Tuple[float, float] = (0.0, -9.81)
    max_contacts_per_pair: int = 4
    enable_warm_starting: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "solver_type": self.solver_type.value,
            "spatial_strategy": self.spatial_strategy.value,
            "quality_level": self.quality_level.value,
            "fixed_timestep": self.fixed_timestep,
            "max_sub_steps": self.max_sub_steps,
            "velocity_iterations": self.velocity_iterations,
            "position_iterations": self.position_iterations,
            "enable_sleeping": self.enable_sleeping,
            "sleep_linear_threshold": self.sleep_linear_threshold,
            "sleep_angular_threshold": self.sleep_angular_threshold,
            "sleep_time_threshold": self.sleep_time_threshold,
            "enable_continuous_collision": self.enable_continuous_collision,
            "gravity": list(self.gravity),
            "max_contacts_per_pair": self.max_contacts_per_pair,
            "enable_warm_starting": self.enable_warm_starting,
        }


@dataclass
class OptimizationRecommendation:
    """A specific optimization recommendation."""
    recommendation_id: str
    target: OptimizationTarget
    description: str
    expected_improvement_pct: float
    difficulty: str  # easy, medium, hard
    current_value: Any = None
    recommended_value: Any = None
    rationale: str = ""
    auto_applicable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "target": self.target.value,
            "description": self.description,
            "expected_improvement_pct": self.expected_improvement_pct,
            "difficulty": self.difficulty,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "rationale": self.rationale,
            "auto_applicable": self.auto_applicable,
        }


class SpatialOptimizer:
    """Optimizes spatial partitioning for collision detection."""

    def recommend_strategy(
        self, body_count: int, active_ratio: float
    ) -> SpatialStrategy:
        """Recommend the best spatial strategy based on scene characteristics."""
        if body_count < 100:
            return SpatialStrategy.GRID_HASH
        elif body_count < 500:
            return SpatialStrategy.SWEEP_AND_PRUNE
        elif body_count < 2000:
            return SpatialStrategy.BOUNDING_VOLUME_HIERARCHY
        elif active_ratio < 0.3:
            return SpatialStrategy.ADAPTIVE_GRID
        else:
            return SpatialStrategy.BOUNDING_VOLUME_HIERARCHY

    def analyze_efficiency(self, profile: PhysicsProfile) -> Dict[str, Any]:
        """Analyze spatial partitioning efficiency."""
        broad_ratio = (
            profile.broad_phase_time_ms / max(profile.total_physics_time_ms, 0.001)
        )
        narrow_ratio = (
            profile.narrow_phase_time_ms / max(profile.total_physics_time_ms, 0.001)
        )

        efficiency = "good"
        if broad_ratio > 0.4:
            efficiency = "poor"
        elif broad_ratio > 0.25:
            efficiency = "fair"

        return {
            "broad_phase_ratio": broad_ratio,
            "narrow_phase_ratio": narrow_ratio,
            "efficiency": efficiency,
            "recommended_strategy": self.recommend_strategy(
                profile.body_count,
                profile.active_body_count / max(profile.body_count, 1),
            ).value,
        }


class SolverOptimizer:
    """Optimizes constraint solver configuration."""

    def recommend_iterations(
        self, constraint_count: int, quality: PhysicsQualityLevel
    ) -> Tuple[int, int]:
        """Recommend velocity and position iteration counts."""
        quality_iters = {
            PhysicsQualityLevel.PRECISION: (20, 8),
            PhysicsQualityLevel.HIGH: (12, 5),
            PhysicsQualityLevel.BALANCED: (8, 3),
            PhysicsQualityLevel.PERFORMANCE: (4, 2),
            PhysicsQualityLevel.MINIMAL: (2, 1),
        }
        base_vel, base_pos = quality_iters.get(quality, (8, 3))

        # Scale with constraint count
        if constraint_count > 500:
            base_vel = max(2, base_vel - 2)
            base_pos = max(1, base_pos - 1)
        elif constraint_count < 50:
            base_vel = min(30, base_vel + 2)

        return base_vel, base_pos

    def recommend_solver(
        self, constraint_count: int, contact_count: int
    ) -> PhysicsSolverType:
        """Recommend the best solver type."""
        if constraint_count < 100:
            return PhysicsSolverType.SEQUENTIAL_IMPULSE
        elif constraint_count < 500:
            return PhysicsSolverType.PROJECTED_GAUSS_SEIDEL
        elif contact_count > 1000:
            return PhysicsSolverType.TEMPORAL_GAUSS_SEIDEL
        else:
            return PhysicsSolverType.NONLINEAR_GAUSS_SEIDEL


class PhysicsOptimizerEngine:
    """Comprehensive physics optimization engine.

    Analyzes physics performance profiles and provides intelligent
    recommendations for optimizing physics simulation across all
    major subsystems including collision detection, constraint solving,
    and spatial partitioning.
    """

    _instance: Optional["PhysicsOptimizerEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use PhysicsOptimizerEngine.get_instance()")
        self._spatial_optimizer = SpatialOptimizer()
        self._solver_optimizer = SolverOptimizer()
        self._profiles: List[PhysicsProfile] = []
        self._config: PhysicsConfiguration = PhysicsConfiguration()
        self._recommendations: List[OptimizationRecommendation] = []
        self._initialized: bool = False
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "PhysicsOptimizerEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, config: Optional[PhysicsConfiguration] = None) -> None:
        """Initialize the physics optimizer."""
        with self._lock:
            if config:
                self._config = config
            self._initialized = True

    def record_profile(self, profile: PhysicsProfile) -> None:
        """Record a physics performance profile for analysis."""
        with self._lock:
            self._profiles.append(profile)
            if len(self._profiles) > 1000:
                self._profiles = self._profiles[-500:]

    def analyze(self) -> List[OptimizationRecommendation]:
        """Analyze current physics performance and generate recommendations."""
        with self._lock:
            if not self._profiles:
                return []

            latest = self._profiles[-1]
            recommendations = []

            # Broad phase optimization
            spatial_analysis = self._spatial_optimizer.analyze_efficiency(latest)
            if spatial_analysis["efficiency"] != "good":
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    target=OptimizationTarget.BROAD_PHASE,
                    description=f"Switch spatial strategy to {spatial_analysis['recommended_strategy']}",
                    expected_improvement_pct=15.0,
                    difficulty="easy",
                    current_value=self._config.spatial_strategy.value,
                    recommended_value=spatial_analysis["recommended_strategy"],
                    rationale=f"Broad phase ratio is {spatial_analysis['broad_phase_ratio']:.2%}",
                    auto_applicable=True,
                ))

            # Solver optimization
            if latest.constraint_count > 200:
                rec_vel, rec_pos = self._solver_optimizer.recommend_iterations(
                    latest.constraint_count, self._config.quality_level
                )
                if rec_vel != self._config.velocity_iterations:
                    recommendations.append(OptimizationRecommendation(
                        recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                        target=OptimizationTarget.CONSTRAINT_SOLVING,
                        description=f"Adjust velocity iterations to {rec_vel}",
                        expected_improvement_pct=10.0,
                        difficulty="easy",
                        current_value=self._config.velocity_iterations,
                        recommended_value=rec_vel,
                        rationale="Optimize solver iterations for constraint count",
                        auto_applicable=True,
                    ))

            # Sleep management
            if latest.sleeping_body_count > 0 and not self._config.enable_sleeping:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    target=OptimizationTarget.SLEEP_MANAGEMENT,
                    description="Enable body sleeping for inactive objects",
                    expected_improvement_pct=20.0,
                    difficulty="easy",
                    current_value=False,
                    recommended_value=True,
                    rationale=f"{latest.sleeping_body_count} bodies could be sleeping",
                    auto_applicable=True,
                ))

            # Timestep optimization
            if latest.total_physics_time_ms > 16.0 and self._config.max_sub_steps > 1:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    target=OptimizationTarget.INTEGRATION,
                    description="Reduce max sub-steps to improve frame budget",
                    expected_improvement_pct=25.0,
                    difficulty="medium",
                    current_value=self._config.max_sub_steps,
                    recommended_value=max(1, self._config.max_sub_steps - 1),
                    rationale=f"Physics time ({latest.total_physics_time_ms:.1f}ms) exceeds frame budget",
                    auto_applicable=True,
                ))

            self._recommendations = recommendations
            return recommendations

    def apply_recommendation(self, recommendation_id: str) -> bool:
        """Apply a specific optimization recommendation."""
        with self._lock:
            for rec in self._recommendations:
                if rec.recommendation_id == recommendation_id and rec.auto_applicable:
                    if rec.target == OptimizationTarget.BROAD_PHASE:
                        try:
                            self._config.spatial_strategy = SpatialStrategy(
                                rec.recommended_value
                            )
                        except ValueError:
                            return False
                    elif rec.target == OptimizationTarget.CONSTRAINT_SOLVING:
                        self._config.velocity_iterations = int(rec.recommended_value)
                    elif rec.target == OptimizationTarget.SLEEP_MANAGEMENT:
                        self._config.enable_sleeping = bool(rec.recommended_value)
                    elif rec.target == OptimizationTarget.INTEGRATION:
                        self._config.max_sub_steps = int(rec.recommended_value)
                    return True
            return False

    def get_configuration(self) -> Dict[str, Any]:
        with self._lock:
            return self._config.to_dict()

    def update_configuration(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update physics configuration parameters."""
        with self._lock:
            for key, value in updates.items():
                if hasattr(self._config, key):
                    if key == "solver_type":
                        try:
                            setattr(self._config, key, PhysicsSolverType(value))
                        except ValueError:
                            pass
                    elif key == "spatial_strategy":
                        try:
                            setattr(self._config, key, SpatialStrategy(value))
                        except ValueError:
                            pass
                    elif key == "quality_level":
                        try:
                            setattr(self._config, key, PhysicsQualityLevel(value))
                        except ValueError:
                            pass
                    elif key == "gravity":
                        self._config.gravity = tuple(value[:2])
                    else:
                        setattr(self._config, key, value)
            return self._config.to_dict()

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "profiles_collected": len(self._profiles),
                "recommendations_count": len(self._recommendations),
                "current_config": self._config.to_dict(),
                "initialized": self._initialized,
                "latest_profile": self._profiles[-1].to_dict() if self._profiles else None,
            }

    def get_recommendations(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._recommendations]

    def get_profiles(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._profiles[-limit:]]


def get_physics_optimizer() -> PhysicsOptimizerEngine:
    """Get the global PhysicsOptimizerEngine instance."""
    return PhysicsOptimizerEngine.get_instance()