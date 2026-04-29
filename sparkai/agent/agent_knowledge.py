"""
SparkAI Agent - Knowledge Graph Engine

A structured knowledge base for the AI-native game engine that stores
game design patterns, code patterns, architecture decisions, and
reusable game components. Supports knowledge inference, pattern
matching, and contextual retrieval.

Architecture:
  KnowledgeGraph
    |-- KnowledgeNode (atomic knowledge unit)
    |-- KnowledgeRelation (typed connections between nodes)
    |-- PatternLibrary (reusable game design patterns)
    |-- InferenceEngine (derive new knowledge from existing)
    |-- ContextRetriever (context-aware knowledge search)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class KnowledgeDomain(Enum):
    GAME_DESIGN = "game_design"
    CODE_PATTERN = "code_pattern"
    ARCHITECTURE = "architecture"
    AI_BEHAVIOR = "ai_behavior"
    RENDERING = "rendering"
    PHYSICS = "physics"
    AUDIO = "audio"
    NARRATIVE = "narrative"
    UI_UX = "ui_ux"
    PERFORMANCE = "performance"
    TOOLING = "tooling"
    TESTING = "testing"


class RelationType(Enum):
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    ALTERNATIVE_TO = "alternative_to"
    COMPOSED_OF = "composed_of"
    CONFLICTS_WITH = "conflicts_with"
    RECOMMENDED_WITH = "recommended_with"
    DERIVED_FROM = "derived_from"
    USED_IN = "used_in"
    OPTIMIZES = "optimizes"


class NodeConfidence(Enum):
    SPECULATIVE = "speculative"
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"
    PROVEN = "proven"
    CANONICAL = "canonical"


class PatternCategory(Enum):
    CREATIONAL = "creational"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    CONCURRENCY = "concurrency"
    OPTIMIZATION = "optimization"
    ANTI_PATTERN = "anti_pattern"


@dataclass
class KnowledgeNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    domain: KnowledgeDomain = KnowledgeDomain.GAME_DESIGN
    confidence: NodeConfidence = NodeConfidence.EXPERIMENTAL
    content: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    version: int = 1
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "domain": self.domain.value,
            "confidence": self.confidence.value,
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "source": self.source,
            "version": self.version,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def touch(self) -> None:
        self.access_count += 1
        self.updated_at = time.time()


@dataclass
class KnowledgeRelation:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.DEPENDS_ON
    weight: float = 1.0
    description: str = ""
    bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "description": self.description,
            "bidirectional": self.bidirectional,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class DesignPattern:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: PatternCategory = PatternCategory.CREATIONAL
    problem: str = ""
    solution: str = ""
    consequences: List[str] = field(default_factory=list)
    applicable_genres: List[str] = field(default_factory=list)
    code_example: str = ""
    related_patterns: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "problem": self.problem,
            "solution": self.solution,
            "consequences": self.consequences,
            "applicable_genres": self.applicable_genres,
            "code_example": self.code_example,
            "related_patterns": self.related_patterns,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
        }


@dataclass
class InferenceResult:
    derived_node: KnowledgeNode
    inference_path: List[str]
    confidence: float
    method: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "derived_node": self.derived_node.to_dict(),
            "inference_path": self.inference_path,
            "confidence": self.confidence,
            "method": self.method,
        }


class InferenceEngine:
    """
    Derives new knowledge from existing nodes and relations.
    Supports transitive, compositional, and analogical inference.
    """

    def __init__(self) -> None:
        self._inference_count: int = 0
        self._inferences: List[InferenceResult] = []

    def infer_transitive(
        self,
        nodes: Dict[str, KnowledgeNode],
        relations: List[KnowledgeRelation],
    ) -> List[InferenceResult]:
        results: List[InferenceResult] = []

        relation_map: Dict[str, List[KnowledgeRelation]] = {}
        for r in relations:
            key = f"{r.source_id}:{r.relation_type.value}"
            relation_map.setdefault(key, []).append(r)

        for r1 in relations:
            transitive_key = f"{r1.target_id}:{r1.relation_type.value}"
            if transitive_key in relation_map:
                for r2 in relation_map[transitive_key]:
                    existing = any(
                        rr.source_id == r1.source_id
                        and rr.target_id == r2.target_id
                        and rr.relation_type == r1.relation_type
                        for rr in relations
                    )
                    if not existing:
                        source_node = nodes.get(r1.source_id)
                        target_node = nodes.get(r2.target_id)
                        if source_node and target_node:
                            derived = KnowledgeNode(
                                title=f"Inferred: {source_node.title} -> {target_node.title}",
                                domain=source_node.domain,
                                confidence=NodeConfidence.SPECULATIVE,
                                content=f"Transitive inference: {source_node.title} {r1.relation_type.value} {target_node.title}",
                                tags=["inferred", "transitive"],
                                source="inference_engine",
                            )
                            confidence = min(r1.weight, r2.weight) * 0.7
                            result = InferenceResult(
                                derived_node=derived,
                                inference_path=[r1.id, r2.id],
                                confidence=confidence,
                                method="transitive",
                            )
                            results.append(result)
                            self._inference_count += 1

        self._inferences.extend(results)
        return results

    def infer_by_composition(
        self,
        nodes: Dict[str, KnowledgeNode],
        relations: List[KnowledgeRelation],
    ) -> List[InferenceResult]:
        results: List[InferenceResult] = []

        composed_of_relations = [r for r in relations if r.relation_type == RelationType.COMPOSED_OF]
        component_map: Dict[str, List[KnowledgeRelation]] = {}
        for r in composed_of_relations:
            component_map.setdefault(r.target_id, []).append(r)

        for target_id, components in component_map.items():
            if len(components) >= 2:
                target_node = nodes.get(target_id)
                if target_node:
                    component_nodes = [nodes.get(c.source_id) for c in components]
                    component_nodes = [n for n in component_nodes if n is not None]

                    if len(component_nodes) >= 2:
                        shared_tags: Set[str] = set(component_nodes[0].tags)
                        for cn in component_nodes[1:]:
                            shared_tags &= set(cn.tags)

                        if shared_tags:
                            derived = KnowledgeNode(
                                title=f"Composite pattern: {target_node.title}",
                                domain=target_node.domain,
                                confidence=NodeConfidence.EXPERIMENTAL,
                                content=f"Components share properties: {', '.join(shared_tags)}",
                                tags=list(shared_tags) + ["inferred", "composite"],
                                source="inference_engine",
                            )
                            result = InferenceResult(
                                derived_node=derived,
                                inference_path=[c.id for c in components],
                                confidence=0.6,
                                method="composition",
                            )
                            results.append(result)
                            self._inference_count += 1

        self._inferences.extend(results)
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_inferences": self._inference_count,
            "by_method": {
                "transitive": sum(1 for i in self._inferences if i.method == "transitive"),
                "composition": sum(1 for i in self._inferences if i.method == "composition"),
            },
        }


class ContextRetriever:
    """
    Context-aware knowledge retrieval that considers domain,
    confidence, tags, and relation proximity.
    """

    def __init__(self, nodes: Dict[str, KnowledgeNode], relations: List[KnowledgeRelation]) -> None:
        self._nodes = nodes
        self._relations = relations

    def search(
        self,
        query: str,
        domain: Optional[KnowledgeDomain] = None,
        min_confidence: Optional[NodeConfidence] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Tuple[KnowledgeNode, float]]:
        scored: List[Tuple[KnowledgeNode, float]] = []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        confidence_order = {
            NodeConfidence.SPECULATIVE: 1,
            NodeConfidence.EXPERIMENTAL: 2,
            NodeConfidence.VALIDATED: 3,
            NodeConfidence.PROVEN: 4,
            NodeConfidence.CANONICAL: 5,
        }

        for node in self._nodes.values():
            if domain and node.domain != domain:
                continue

            if min_confidence:
                if confidence_order.get(node.confidence, 0) < confidence_order.get(min_confidence, 0):
                    continue

            score = 0.0

            title_words = set(node.title.lower().split())
            content_words = set(node.content.lower().split())
            all_words = title_words | content_words

            score += len(query_words & title_words) * 3.0
            score += len(query_words & content_words) * 1.0

            if tags:
                tag_match = len(set(tags) & set(node.tags))
                score += tag_match * 2.0

            score += confidence_order.get(node.confidence, 0) * 0.5
            score += min(node.access_count * 0.1, 2.0)

            if score > 0:
                scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def get_related(
        self,
        node_id: str,
        max_depth: int = 2,
        relation_types: Optional[List[RelationType]] = None,
    ) -> List[Tuple[KnowledgeNode, int]]:
        if node_id not in self._nodes:
            return []

        visited: Set[str] = {node_id}
        result: List[Tuple[KnowledgeNode, int]] = []
        queue: List[Tuple[str, int]] = [(node_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for relation in self._relations:
                if relation_types and relation.relation_type not in relation_types:
                    continue

                neighbor_id = None
                if relation.source_id == current_id:
                    neighbor_id = relation.target_id
                elif relation.bidirectional and relation.target_id == current_id:
                    neighbor_id = relation.source_id

                if neighbor_id and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor_node = self._nodes.get(neighbor_id)
                    if neighbor_node:
                        result.append((neighbor_node, depth + 1))
                        queue.append((neighbor_id, depth + 1))

        return result


class KnowledgeGraph:
    """
    Central knowledge management system for the SparkLabs AI-native game engine.

    Stores, retrieves, and infers knowledge about game design patterns,
    code patterns, architecture decisions, and reusable components.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._relations: List[KnowledgeRelation] = []
        self._patterns: Dict[str, DesignPattern] = {}
        self._inference_engine = InferenceEngine()
        self._node_count: int = 0
        self._relation_count: int = 0
        self._pattern_count: int = 0
        self._query_count: int = 0
        self._seed_knowledge()

    def _seed_knowledge(self) -> None:
        seed_nodes = [
            ("entity_component", "Entity-Component-System Architecture", KnowledgeDomain.ARCHITECTURE,
             NodeConfidence.CANONICAL, "Decompose game objects into entities, components, and systems for flexible composition", ["ecs", "architecture", "composition"]),
            ("observer_pattern", "Observer Pattern for Game Events", KnowledgeDomain.CODE_PATTERN,
             NodeConfidence.PROVEN, "Decouple event producers from consumers using observer pattern for game event systems", ["events", "observer", "decoupling"]),
            ("state_machine", "Finite State Machine for AI", KnowledgeDomain.AI_BEHAVIOR,
             NodeConfidence.PROVEN, "Model agent behavior as discrete states with defined transitions for predictable AI", ["fsm", "ai", "behavior"]),
            ("object_pool", "Object Pool for Performance", KnowledgeDomain.PERFORMANCE,
             NodeConfidence.PROVEN, "Reuse objects instead of creating/destroying to reduce garbage collection pressure", ["pool", "memory", "optimization"]),
            ("command_pattern", "Command Pattern for Input", KnowledgeDomain.CODE_PATTERN,
             NodeConfidence.VALIDATED, "Encapsulate actions as objects for undo/redo, replay, and input binding", ["command", "input", "undo"]),
            ("spatial_hash", "Spatial Hashing for Collision", KnowledgeDomain.PHYSICS,
             NodeConfidence.VALIDATED, "Partition space into grid cells for O(1) broad-phase collision detection", ["collision", "spatial", "hash"]),
            ("behavior_tree", "Behavior Tree for Complex AI", KnowledgeDomain.AI_BEHAVIOR,
             NodeConfidence.PROVEN, "Hierarchical task composition for complex AI decision making", ["behavior_tree", "ai", "hierarchy"]),
            ("scene_graph", "Scene Graph for Transform Hierarchy", KnowledgeDomain.ARCHITECTURE,
             NodeConfidence.CANONICAL, "Organize game objects in a tree for hierarchical transform propagation", ["scene", "transform", "hierarchy"]),
            ("double_buffer", "Double Buffer for Rendering", KnowledgeDomain.RENDERING,
             NodeConfidence.PROVEN, "Use two buffers to prevent tearing and ensure smooth frame presentation", ["rendering", "buffer", "vsync"]),
            ("flyweight", "Flyweight Pattern for Shared Data", KnowledgeDomain.PERFORMANCE,
             NodeConfidence.VALIDATED, "Share common data across instances to reduce memory usage", ["flyweight", "memory", "sharing"]),
        ]

        for nid, title, domain, confidence, content, tags in seed_nodes:
            node = KnowledgeNode(
                id=nid,
                title=title,
                domain=domain,
                confidence=confidence,
                content=content,
                tags=tags,
                source="sparklabs_core",
            )
            self._nodes[nid] = node
            self._node_count += 1

        seed_relations = [
            ("entity_component", "scene_graph", RelationType.IMPLEMENTS, "ECS uses scene graph for entity hierarchy"),
            ("state_machine", "behavior_tree", RelationType.ALTERNATIVE_TO, "FSM is simpler but less flexible than behavior trees"),
            ("object_pool", "flyweight", RelationType.RECOMMENDED_WITH, "Object pools and flyweight complement each other"),
            ("observer_pattern", "command_pattern", RelationType.COMPOSED_OF, "Commands can trigger observers"),
            ("spatial_hash", "entity_component", RelationType.USED_IN, "Spatial hashing works with ECS for collision"),
            ("double_buffer", "scene_graph", RelationType.DEPENDS_ON, "Rendering double buffers scene graph state"),
            ("behavior_tree", "entity_component", RelationType.USED_IN, "Behavior trees integrate with ECS AI components"),
            ("command_pattern", "state_machine", RelationType.EXTENDS, "Commands can trigger state transitions"),
        ]

        for source_id, target_id, rtype, desc in seed_relations:
            relation = KnowledgeRelation(
                source_id=source_id,
                target_id=target_id,
                relation_type=rtype,
                description=desc,
            )
            self._relations.append(relation)
            self._relation_count += 1

        seed_patterns = [
            ("game_loop", "Game Loop Pattern", PatternCategory.BEHAVIORAL,
             "Need a central update cycle that processes input, updates state, and renders output",
             "Implement a fixed or variable timestep loop with input->update->render phases",
             ["Deterministic with fixed timestep", "Simpler with variable timestep"], ["all"]),
            ("component_factory", "Component Factory", PatternCategory.CREATIONAL,
             "Need to create components dynamically without knowing concrete types",
             "Register component types with a factory that creates instances by type name",
             ["Decoupled creation", "Runtime type registration"], ["all"]),
            ("service_locator", "Service Locator", PatternCategory.STRUCTURAL,
             "Need global access to services without tight coupling",
             "Central registry that provides access to shared services by interface type",
             ["Flexible dependency access", "Can hide singleton pattern"], ["all"]),
        ]

        for pid, name, cat, problem, solution, consequences, genres in seed_patterns:
            pattern = DesignPattern(
                id=pid,
                name=name,
                category=cat,
                problem=problem,
                solution=solution,
                consequences=consequences,
                applicable_genres=genres,
                tags=[cat.value],
            )
            self._patterns[pid] = pattern
            self._pattern_count += 1

    def add_node(
        self,
        title: str,
        domain: str = "game_design",
        confidence: str = "experimental",
        content: str = "",
        tags: Optional[List[str]] = None,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeNode:
        domain_enum = KnowledgeDomain(domain)
        conf_enum = NodeConfidence(confidence)
        node = KnowledgeNode(
            title=title,
            domain=domain_enum,
            confidence=conf_enum,
            content=content,
            tags=tags or [],
            source=source,
            metadata=metadata or {},
        )
        self._nodes[node.id] = node
        self._node_count += 1
        return node

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        node = self._nodes.get(node_id)
        if node:
            node.touch()
            return node.to_dict()
        return None

    def update_node(self, node_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        node = self._nodes.get(node_id)
        if not node:
            return None

        if "title" in updates:
            node.title = updates["title"]
        if "content" in updates:
            node.content = updates["content"]
        if "tags" in updates:
            node.tags = updates["tags"]
        if "domain" in updates:
            node.domain = KnowledgeDomain(updates["domain"])
        if "confidence" in updates:
            node.confidence = NodeConfidence(updates["confidence"])
        if "metadata" in updates:
            node.metadata.update(updates["metadata"])

        node.version += 1
        node.updated_at = time.time()
        return node.to_dict()

    def remove_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            self._relations = [
                r for r in self._relations
                if r.source_id != node_id and r.target_id != node_id
            ]
            self._node_count -= 1
            return True
        return False

    def list_nodes(
        self,
        domain: Optional[KnowledgeDomain] = None,
        confidence: Optional[NodeConfidence] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        nodes = list(self._nodes.values())

        if domain:
            nodes = [n for n in nodes if n.domain == domain]
        if confidence:
            nodes = [n for n in nodes if n.confidence == confidence]
        if tags:
            nodes = [n for n in nodes if any(t in n.tags for t in tags)]

        nodes.sort(key=lambda n: n.updated_at, reverse=True)
        return [n.to_dict() for n in nodes[:limit]]

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str = "depends_on",
        weight: float = 1.0,
        description: str = "",
        bidirectional: bool = False,
    ) -> Optional[KnowledgeRelation]:
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        relation = KnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=RelationType(relation_type),
            weight=weight,
            description=description,
            bidirectional=bidirectional,
        )
        self._relations.append(relation)
        self._relation_count += 1
        return relation

    def remove_relation(self, relation_id: str) -> bool:
        before = len(self._relations)
        self._relations = [r for r in self._relations if r.id != relation_id]
        removed = len(self._relations) < before
        if removed:
            self._relation_count -= 1
        return removed

    def list_relations(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relation_type: Optional[RelationType] = None,
    ) -> List[Dict[str, Any]]:
        relations = self._relations
        if source_id:
            relations = [r for r in relations if r.source_id == source_id]
        if target_id:
            relations = [r for r in relations if r.target_id == target_id]
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]
        return [r.to_dict() for r in relations]

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        min_confidence: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        self._query_count += 1
        retriever = ContextRetriever(self._nodes, self._relations)

        domain_enum = KnowledgeDomain(domain) if domain else None
        conf_enum = NodeConfidence(min_confidence) if min_confidence else None

        results = retriever.search(query, domain_enum, conf_enum, tags, limit)
        return [
            {"node": node.to_dict(), "relevance_score": score}
            for node, score in results
        ]

    def get_related(
        self,
        node_id: str,
        max_depth: int = 2,
        relation_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        retriever = ContextRetriever(self._nodes, self._relations)
        rtypes = [RelationType(rt) for rt in relation_types] if relation_types else None
        results = retriever.get_related(node_id, max_depth, rtypes)
        return [
            {"node": node.to_dict(), "distance": distance}
            for node, distance in results
        ]

    def run_inference(self, method: str = "all") -> List[Dict[str, Any]]:
        if method in ("all", "transitive"):
            transitive = self._inference_engine.infer_transitive(self._nodes, self._relations)
        else:
            transitive = []

        if method in ("all", "composition"):
            compositional = self._inference_engine.infer_by_composition(self._nodes, self._relations)
        else:
            compositional = []

        all_results = transitive + compositional
        return [r.to_dict() for r in all_results]

    def add_pattern(
        self,
        name: str,
        category: str = "creational",
        problem: str = "",
        solution: str = "",
        consequences: Optional[List[str]] = None,
        applicable_genres: Optional[List[str]] = None,
        code_example: str = "",
        tags: Optional[List[str]] = None,
    ) -> DesignPattern:
        pattern = DesignPattern(
            name=name,
            category=PatternCategory(category),
            problem=problem,
            solution=solution,
            consequences=consequences or [],
            applicable_genres=applicable_genres or [],
            code_example=code_example,
            tags=tags or [],
        )
        self._patterns[pattern.id] = pattern
        self._pattern_count += 1
        return pattern

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        pattern = self._patterns.get(pattern_id)
        if pattern:
            pattern.usage_count += 1
            return pattern.to_dict()
        return None

    def list_patterns(
        self,
        category: Optional[PatternCategory] = None,
        genre: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        patterns = list(self._patterns.values())
        if category:
            patterns = [p for p in patterns if p.category == category]
        if genre:
            patterns = [p for p in patterns if genre in p.applicable_genres or "all" in p.applicable_genres]
        return [p.to_dict() for p in patterns]

    def find_patterns_for_problem(self, problem: str) -> List[Dict[str, Any]]:
        problem_lower = problem.lower()
        problem_words = set(problem_lower.split())

        scored: List[Tuple[DesignPattern, float]] = []
        for pattern in self._patterns.values():
            pattern_words = set(pattern.problem.lower().split())
            overlap = len(problem_words & pattern_words)
            if overlap > 0:
                scored.append((pattern, overlap))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [p.to_dict() for p, _ in scored[:10]]

    def get_graph_stats(self) -> Dict[str, Any]:
        domain_counts: Dict[str, int] = {}
        confidence_counts: Dict[str, int] = {}
        relation_type_counts: Dict[str, int] = {}

        for node in self._nodes.values():
            domain_counts[node.domain.value] = domain_counts.get(node.domain.value, 0) + 1
            confidence_counts[node.confidence.value] = confidence_counts.get(node.confidence.value, 0) + 1

        for relation in self._relations:
            key = relation.relation_type.value
            relation_type_counts[key] = relation_type_counts.get(key, 0) + 1

        return {
            "total_nodes": self._node_count,
            "total_relations": self._relation_count,
            "total_patterns": self._pattern_count,
            "total_queries": self._query_count,
            "by_domain": domain_counts,
            "by_confidence": confidence_counts,
            "by_relation_type": relation_type_counts,
            "inference_stats": self._inference_engine.get_stats(),
        }


_global_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _global_knowledge_graph
    if _global_knowledge_graph is None:
        _global_knowledge_graph = KnowledgeGraph()
    return _global_knowledge_graph
