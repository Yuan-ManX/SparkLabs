"""
SparkLabs Engine - Game State Analyzer

A comprehensive real-time game state analysis system that provides deep
understanding of game scenes, entity relationships, gameplay flow metrics,
and systemic interaction analysis for runtime optimization and debugging.

Architecture:
  GameStateAnalyzer (singleton)
    |-- SceneAnalysis (complete breakdown of a game scene)
    |-- EntityRelationship (typed relationship between game entities)
    |-- GameplayFlowMetrics (quantitative metrics of gameplay quality)
    |-- SystemicInteraction (cross-system interaction analysis)
    |-- AnalysisDomain (categories of game state analysis)
    |-- SceneState (time-stamped snapshot of scene composition)

Core Capabilities:
  - analyze_scene: Full breakdown of scene entity composition and relationships
  - compute_flow_metrics: Quantitative gameplay flow and pacing analysis
  - detect_bottlenecks: Identify performance and gameplay bottlenecks
  - analyze_systemic_interactions: Map cross-system entity interactions
  - compare_scenes: Side-by-side scene comparison for iteration
  - track_state_changes: Monitor and categorize scene mutations over time
  - generate_optimization_hints: Suggest targeted scene optimizations
  - validate_scene_integrity: Check scene against quality and performance rules
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


class AnalysisDomain(Enum):
    COMPOSITION = "composition"
    PERFORMANCE = "performance"
    GAMEPLAY = "gameplay"
    RELATIONSHIPS = "relationships"
    SYSTEMS = "systems"
    PACING = "pacing"
    BALANCE = "balance"
    ACCESSIBILITY = "accessibility"


class EntityType(Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    NPC = "npc"
    COLLECTIBLE = "collectible"
    OBSTACLE = "obstacle"
    TRIGGER = "trigger"
    DECORATIVE = "decorative"
    LIGHT = "light"
    PARTICLE = "particle"
    AUDIO = "audio"
    UI_ELEMENT = "ui_element"
    CAMERA = "camera"
    UNKNOWN = "unknown"


class RelationshipType(Enum):
    COLLISION = "collision"
    ATTACHMENT = "attachment"
    SCRIPTING = "scripting"
    PARENT_CHILD = "parent_child"
    DEPENDENCY = "dependency"
    SIGNAL_LISTENER = "signal_listener"
    PROXIMITY = "proximity"
    CUSTOM = "custom"


class BottleneckSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SceneStateCategory(Enum):
    ENTITY_ADDED = "entity_added"
    ENTITY_REMOVED = "entity_removed"
    PROPERTY_CHANGED = "property_changed"
    RELATIONSHIP_CHANGED = "relationship_changed"
    SYSTEM_MODIFIED = "system_modified"
    LAYOUT_CHANGED = "layout_changed"


@dataclass
class EntityRelationship:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    relationship_type: str = RelationshipType.CUSTOM.value
    strength: float = 0.5
    distance: float = 0.0
    interaction_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "distance": self.distance,
            "interaction_count": self.interaction_count,
            "metadata": self.metadata,
        }


@dataclass
class SceneSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_id: str = ""
    timestamp: float = field(default_factory=_time_module.time)
    entity_count: int = 0
    entity_type_distribution: Dict[str, int] = field(default_factory=dict)
    active_systems: List[str] = field(default_factory=list)
    estimated_memory: int = 0
    render_objects: int = 0
    active_scripts: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scene_id": self.scene_id,
            "timestamp": self.timestamp,
            "entity_count": self.entity_count,
            "entity_type_distribution": self.entity_type_distribution,
            "active_systems": self.active_systems,
            "estimated_memory": self.estimated_memory,
            "render_objects": self.render_objects,
            "active_scripts": self.active_scripts,
            "tags": self.tags,
        }


@dataclass
class SystemicInteraction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_system: str = ""
    target_system: str = ""
    interaction_type: str = "data_flow"
    entity_count: int = 0
    frequency: float = 0.0
    complexity_score: float = 0.0
    coupling_strength: float = 0.0
    risk_assessment: str = ""
    optimization_potential: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_system": self.source_system,
            "target_system": self.target_system,
            "interaction_type": self.interaction_type,
            "entity_count": self.entity_count,
            "frequency": self.frequency,
            "complexity_score": self.complexity_score,
            "coupling_strength": self.coupling_strength,
            "risk_assessment": self.risk_assessment,
            "optimization_potential": self.optimization_potential,
        }


_SCENE_QUALITY_RULES: Dict[str, Dict[str, Any]] = {
    "max_entities_per_scene": {
        "threshold": 500,
        "severity": BottleneckSeverity.HIGH.value,
        "message": "Scene contains more than {value} entities; consider using object pooling or spatial partitioning",
    },
    "min_entity_variety": {
        "threshold": 3,
        "severity": BottleneckSeverity.INFO.value,
        "message": "Scene has less than {value} entity types; consider adding more gameplay variety",
    },
    "player_proximity_ratio": {
        "threshold": 0.3,
        "severity": BottleneckSeverity.MEDIUM.value,
        "message": "More than {percentage}% of entities are close to the player; consider spreading out content",
    },
    "trigger_density": {
        "threshold": 10,
        "severity": BottleneckSeverity.MEDIUM.value,
        "message": "More than {value} triggers in one area; may cause overlapping activation issues",
    },
    "entity_depth_excessive": {
        "threshold": 8,
        "severity": BottleneckSeverity.LOW.value,
        "message": "Entity hierarchy exceeds {value} levels deep; consider flattening for performance",
    },
}


_PERFORMANCE_THRESHOLDS: Dict[str, Tuple[float, str]] = {
    "entity_count": (300, "Consider object pooling or LOD culling"),
    "active_scripts": (50, "Too many active scripts; consider batching or reducing tick rate"),
    "render_objects": (400, "High draw call count; consider mesh combining or instancing"),
    "relationship_graph_depth": (4, "Complex entity relationship graph; may impact update performance"),
}


class GameStateAnalyzer:
    _instance: Optional[GameStateAnalyzer] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> GameStateAnalyzer:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> GameStateAnalyzer:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._scenes: Dict[str, Dict[str, Any]] = {}
        self._relationships: Dict[str, List[EntityRelationship]] = defaultdict(list)
        self._snapshots: Dict[str, List[SceneSnapshot]] = defaultdict(list)
        self._interactions: Dict[str, List[SystemicInteraction]] = defaultdict(list)
        self._bottlenecks: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._state_changes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        self._total_analyses: int = 0
        self._total_scenes: int = 0
        self._total_snapshots: int = 0
        self._total_bottlenecks_detected: int = 0

    def register_scene(
        self,
        scene_id: str,
        scene_name: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        active_systems: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entities = entities or []
        active_systems = active_systems or []
        metadata = metadata or {}

        entity_types: Set[str] = set()
        for entity in entities:
            entity_type = entity.get("type", EntityType.UNKNOWN.value)
            entity_types.add(entity_type)

        scene_data = {
            "scene_id": scene_id,
            "scene_name": scene_name,
            "entity_count": len(entities),
            "entity_types": list(entity_types),
            "active_systems": active_systems,
            "metadata": metadata,
            "created_at": _time_module.time(),
            "updated_at": _time_module.time(),
        }
        self._scenes[scene_id] = scene_data
        self._total_scenes = max(self._total_scenes, len(self._scenes))

        return scene_data

    def take_snapshot(self, scene_id: str, tags: Optional[List[str]] = None) -> Optional[SceneSnapshot]:
        if scene_id not in self._scenes:
            return None

        scene = self._scenes[scene_id]
        type_distribution: Dict[str, int] = {}
        for etype in scene.get("entity_types", []):
            type_distribution[etype] = type_distribution.get(etype, 0) + 1

        snapshot = SceneSnapshot(
            scene_id=scene_id,
            entity_count=scene["entity_count"],
            entity_type_distribution=type_distribution,
            active_systems=scene.get("active_systems", []),
            estimated_memory=scene["entity_count"] * 2048,
            render_objects=scene["entity_count"] - (scene["entity_count"] // 4),
            active_scripts=max(1, scene["entity_count"] // 3),
            tags=tags or [],
        )
        self._snapshots[scene_id].append(snapshot)
        self._total_snapshots += 1
        return snapshot

    def analyze_scene(
        self,
        scene_id: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        analysis_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        scene = self._scenes.get(scene_id)
        if not scene:
            scene = self.register_scene(scene_id, f"Scene_{scene_id}")
            self._scenes[scene_id] = scene

        entities = entities or []
        analysis_domains = analysis_domains or [d.value for d in AnalysisDomain]
        entity_count = max(scene["entity_count"], len(entities))

        entity_type_counts: Dict[str, int] = {}
        for entity in entities:
            etype = entity.get("type", EntityType.UNKNOWN.value)
            entity_type_counts[etype] = entity_type_counts.get(etype, 0) + 1

        bottlenecks = self._detect_scene_bottlenecks(scene_id, entity_count, entity_type_counts)

        performance_metrics = {}
        for metric, (threshold, hint) in _PERFORMANCE_THRESHOLDS.items():
            current_value = entity_count if metric == "entity_count" else entity_count // 2
            performance_metrics[metric] = {
                "current": current_value,
                "threshold": threshold,
                "status": "warning" if current_value > threshold else "ok",
                "hint": hint if current_value > threshold else "",
            }

        flow_metrics = self._compute_flow_metrics(scene_id, entities)

        analysis = {
            "scene_id": scene_id,
            "scene_name": scene.get("scene_name", f"Scene_{scene_id}"),
            "entity_count": entity_count,
            "entity_type_distribution": entity_type_counts,
            "active_systems": scene.get("active_systems", []),
            "relationships_count": len(self._relationships.get(scene_id, [])),
            "snapshot_count": len(self._snapshots.get(scene_id, [])),
            "bottlenecks": bottlenecks,
            "bottleneck_count": len(bottlenecks),
            "performance_metrics": performance_metrics,
            "flow_metrics": flow_metrics,
            "domains_analyzed": analysis_domains,
            "quality_score": self._compute_quality_score(bottlenecks, entity_count),
        }

        self._total_analyses += 1
        return analysis

    def _detect_scene_bottlenecks(
        self,
        scene_id: str,
        entity_count: int,
        entity_type_counts: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        bottlenecks = []

        for rule_id, rule in _SCENE_QUALITY_RULES.items():
            threshold = rule["threshold"]
            if rule_id == "max_entities_per_scene" and entity_count > threshold:
                bottlenecks.append({
                    "rule_id": rule_id,
                    "severity": rule["severity"],
                    "message": rule["message"].format(value=threshold),
                    "current_value": entity_count,
                    "threshold": threshold,
                })
            elif rule_id == "min_entity_variety" and len(entity_type_counts) < threshold:
                bottlenecks.append({
                    "rule_id": rule_id,
                    "severity": rule["severity"],
                    "message": rule["message"].format(value=threshold),
                    "current_value": len(entity_type_counts),
                    "threshold": threshold,
                })

        self._bottlenecks[scene_id] = bottlenecks
        self._total_bottlenecks_detected += len(bottlenecks)
        return bottlenecks

    def _compute_flow_metrics(
        self,
        scene_id: str,
        entities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        entity_count = len(entities)
        relationship_count = len(self._relationships.get(scene_id, []))

        density = min(1.0, entity_count / 200.0)
        interaction_complexity = min(1.0, relationship_count / max(entity_count, 1) * 5)

        return {
            "entity_density": round(density, 3),
            "interaction_complexity": round(interaction_complexity, 3),
            "pacing_score": round(1.0 - abs(0.4 - density) * 2, 3),
            "navigation_complexity": round(0.3 + 0.5 * density, 3),
            "engagement_density": round(0.2 + 0.6 * density * interaction_complexity, 3),
            "recommended_entity_spread": max(1, int(entity_count * 0.3)),
        }

    def _compute_quality_score(
        self,
        bottlenecks: List[Dict[str, Any]],
        entity_count: int,
    ) -> float:
        severity_weights = {
            BottleneckSeverity.CRITICAL.value: 30,
            BottleneckSeverity.HIGH.value: 20,
            BottleneckSeverity.MEDIUM.value: 10,
            BottleneckSeverity.LOW.value: 5,
            BottleneckSeverity.INFO.value: 2,
        }

        penalty = sum(severity_weights.get(b["severity"], 0) for b in bottlenecks)
        score = max(0.0, min(100.0, 100.0 - penalty * 2))
        return round(score, 1)

    def map_relationships(
        self,
        scene_id: str,
        entities: List[Dict[str, Any]],
        relationship_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> List[EntityRelationship]:
        self._relationships[scene_id] = []
        positions: Dict[str, Tuple[float, float]] = {}

        for entity in entities:
            eid = entity.get("id", str(uuid.uuid4().hex))
            x = entity.get("x", 0.0)
            y = entity.get("y", 0.0)
            positions[eid] = (x, y)

        entity_ids = list(positions.keys())
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                id_a, id_b = entity_ids[i], entity_ids[j]
                ax, ay = positions[id_a]
                bx, by = positions[id_b]
                dist = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

                rel_type = RelationshipType.PROXIMITY.value
                if dist < 50:
                    rel_type = RelationshipType.COLLISION.value
                elif dist < 150:
                    rel_type = RelationshipType.PROXIMITY.value

                relationship = EntityRelationship(
                    source_id=id_a,
                    target_id=id_b,
                    relationship_type=rel_type,
                    strength=max(0.0, 1.0 - dist / 300.0),
                    distance=dist,
                    interaction_count=1,
                )
                self._relationships[scene_id].append(relationship)

        return self._relationships[scene_id]

    def analyze_systemic_interactions(
        self,
        scene_id: str,
        system_pairs: Optional[List[Tuple[str, str]]] = None,
    ) -> List[SystemicInteraction]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return []

        systems = scene.get("active_systems", [])
        system_pairs = system_pairs or []

        if not system_pairs and len(systems) >= 2:
            for i in range(len(systems)):
                for j in range(i + 1, len(systems)):
                    system_pairs.append((systems[i], systems[j]))

        interactions = []
        for src, tgt in system_pairs:
            interaction = SystemicInteraction(
                source_system=src,
                target_system=tgt,
                interaction_type="data_flow" if src != tgt else "self_referential",
                entity_count=scene.get("entity_count", 10),
                frequency=0.5,
                complexity_score=0.3 + 0.4 * (len(scene.get("active_systems", [])) / 10),
                coupling_strength=0.4,
                risk_assessment="Low risk" if len(systems) < 5 else "Moderate coupling risk",
                optimization_potential=0.3,
            )
            interactions.append(interaction)

        self._interactions[scene_id] = interactions
        return interactions

    def generate_optimization_hints(self, scene_id: str) -> Dict[str, Any]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return {"error": f"Scene '{scene_id}' not found"}

        bottlenecks = self._bottlenecks.get(scene_id, [])
        entity_count = scene.get("entity_count", 0)
        relationship_count = len(self._relationships.get(scene_id, []))

        hints = []
        if entity_count > 200:
            hints.append({
                "category": "performance",
                "priority": "high",
                "hint": "Implement spatial partitioning (grid or quadtree) for large entity counts",
                "expected_improvement": "30-50% reduction in proximity queries",
            })
        if relationship_count > entity_count * 2:
            hints.append({
                "category": "memory",
                "priority": "medium",
                "hint": "Prune weak entity relationships to reduce update overhead",
                "expected_improvement": "15-25% reduction in per-frame relationship checks",
            })
        if any(b["severity"] in ("critical", "high") for b in bottlenecks):
            hints.append({
                "category": "architecture",
                "priority": "critical",
                "hint": "Address critical scene bottlenecks before adding more content",
                "expected_improvement": "Significant scene stability improvement",
            })

        hints.append({
            "category": "general",
            "priority": "low",
            "hint": "Profile entity update cycle to identify micro-optimizations",
            "expected_improvement": "5-10% frametime reduction",
        })

        return {
            "scene_id": scene_id,
            "hints": hints,
            "hint_count": len(hints),
            "bottleneck_count": len(bottlenecks),
            "entity_count": entity_count,
            "relationship_count": relationship_count,
        }

    def compare_scenes(self, scene_ids: List[str]) -> Dict[str, Any]:
        results = {}
        for sid in scene_ids:
            scene = self._scenes.get(sid)
            if not scene:
                continue
            bottlenecks = self._bottlenecks.get(sid, [])
            results[sid] = {
                "name": scene.get("scene_name", f"Scene_{sid}"),
                "entity_count": scene.get("entity_count", 0),
                "system_count": len(scene.get("active_systems", [])),
                "bottleneck_count": len(bottlenecks),
                "relationships": len(self._relationships.get(sid, [])),
                "snapshots": len(self._snapshots.get(sid, [])),
            }

        return {
            "compared_scenes": results,
            "most_complex": max(results.keys(), key=lambda s: results[s]["entity_count"]) if results else None,
            "most_optimized": min(results.keys(), key=lambda s: results[s]["bottleneck_count"]) if results else None,
        }

    def track_state_changes(
        self,
        scene_id: str,
        changes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if scene_id not in self._state_changes:
            self._state_changes[scene_id] = []

        for change in changes:
            change["timestamp"] = _time_module.time()
            change["record_id"] = uuid.uuid4().hex
            self._state_changes[scene_id].append(change)

        return {
            "scene_id": scene_id,
            "changes_recorded": len(changes),
            "total_changes": len(self._state_changes[scene_id]),
        }

    def validate_scene_integrity(self, scene_id: str) -> Dict[str, Any]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return {"valid": False, "error": f"Scene '{scene_id}' not found"}

        issues = []
        warnings = []

        entity_count = scene.get("entity_count", 0)
        if entity_count == 0:
            issues.append("Scene has no registered entities")
        if entity_count > 500:
            issues.append(f"Scene has {entity_count} entities (recommended max: 500)")

        systems = scene.get("active_systems", [])
        if not systems:
            warnings.append("No active systems registered for this scene")

        bottlenecks = self._bottlenecks.get(scene_id, [])
        critical_bottlenecks = [b for b in bottlenecks if b["severity"] == BottleneckSeverity.CRITICAL.value]

        return {
            "scene_id": scene_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "critical_bottlenecks": len(critical_bottlenecks),
            "total_bottlenecks": len(bottlenecks),
            "snapshot_count": len(self._snapshots.get(scene_id, [])),
            "changes_tracked": len(self._state_changes.get(scene_id, [])),
        }

    def get_stats(self) -> Dict[str, Any]:
        total_relationships = sum(len(rels) for rels in self._relationships.values())
        total_changes = sum(len(changes) for changes in self._state_changes.values())

        return {
            "total_scenes": len(self._scenes),
            "total_analyses": self._total_analyses,
            "total_snapshots": self._total_snapshots,
            "total_bottlenecks_detected": self._total_bottlenecks_detected,
            "total_relationships": total_relationships,
            "total_state_changes_tracked": total_changes,
            "scenes_with_bottlenecks": sum(
                1 for bl in self._bottlenecks.values() if bl
            ),
            "average_entities_per_scene": round(
                sum(s.get("entity_count", 0) for s in self._scenes.values()) / max(len(self._scenes), 1), 1
            ),
            "quality_rules_available": len(_SCENE_QUALITY_RULES),
            "performance_thresholds_available": len(_PERFORMANCE_THRESHOLDS),
        }


def get_game_state_analyzer() -> GameStateAnalyzer:
    return GameStateAnalyzer.get_instance()