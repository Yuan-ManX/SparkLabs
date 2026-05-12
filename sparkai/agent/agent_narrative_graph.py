"""
SparkLabs Agent - Narrative Graph Engine

Branching story design system for AI-native game creation.
Manages narrative nodes, conditional paths, choice trees,
and graph validation to enable complex interactive storytelling.

Architecture:
  NarrativeGraphEngine
    |-- NarrativeNode (individual story beat or branch point)
    |-- NarrativeGraph (complete branching story structure)
    |-- PathTraverser (pathfinding through narrative space)
    |-- ConditionEvaluator (runtime condition checking)
    |-- GraphValidator (structural integrity and dead-end detection)

Graph Types:
  - Linear: single path with no branching
  - Branching: multiple paths from choice points
  - Convergent: branches that merge back to main line
  - Network: fully interconnected narrative web
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class NarrativeNodeType(Enum):
    PLOT_POINT = "plot_point"
    DIALOGUE = "dialogue"
    CHOICE = "choice"
    BRANCH = "branch"
    MERGE = "merge"
    ENDING = "ending"
    SIDE_QUEST = "side_quest"
    LORE = "lore"


class NarrativeCondition(Enum):
    FLAG_CHECK = "flag_check"
    ITEM_CHECK = "item_check"
    REPUTATION_CHECK = "reputation_check"
    SKILL_CHECK = "skill_check"
    RELATIONSHIP_CHECK = "relationship_check"
    RANDOM_CHANCE = "random_chance"


class NarrativeImpact(Enum):
    FLAG_SET = "flag_set"
    ITEM_GRANT = "item_grant"
    REPUTATION_CHANGE = "reputation_change"
    RELATIONSHIP_CHANGE = "relationship_change"
    AREA_UNLOCK = "area_unlock"


@dataclass
class NarrativeNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    node_type: NarrativeNodeType = NarrativeNodeType.PLOT_POINT
    content_description: str = ""
    speaker: str = ""
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    impacts: List[Dict[str, Any]] = field(default_factory=list)
    child_nodes: List[str] = field(default_factory=list)
    priority: int = 1
    is_optional: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "node_type": self.node_type.value,
            "content_description": self.content_description[:200],
            "speaker": self.speaker,
            "conditions": self.conditions,
            "impacts": self.impacts,
            "child_nodes": self.child_nodes,
            "child_count": len(self.child_nodes),
            "priority": self.priority,
            "is_optional": self.is_optional,
        }


@dataclass
class NarrativeGraph:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    root_node_id: str = ""
    nodes: Dict[str, NarrativeNode] = field(default_factory=dict)
    total_nodes: int = 0
    branching_depth: int = 0
    ending_count: int = 0
    main_quest_line: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "root_node_id": self.root_node_id,
            "node_count": len(self.nodes),
            "total_nodes": self.total_nodes,
            "branching_depth": self.branching_depth,
            "ending_count": self.ending_count,
            "main_quest_line": self.main_quest_line,
            "nodes": [n.to_dict() for n in self.nodes.values()],
        }


class NarrativeGraphEngine:
    """
    Narrative graph engine for branching story design.

    Manages narrative nodes, conditional paths, and choice trees
    to enable complex interactive storytelling in AI-native games.
    """

    _instance: Optional[NarrativeGraphEngine] = None

    @classmethod
    def get_instance(cls) -> NarrativeGraphEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._graphs: Dict[str, NarrativeGraph] = {}
        self._graph_count: int = 0
        self._edge_list: List[Tuple[str, str]] = []
        self._orphaned_nodes: Set[str] = set()

    def create_graph(
        self, title: str, root_data: Dict[str, Any]
    ) -> NarrativeGraph:
        graph = NarrativeGraph(title=title)
        root = NarrativeNode(
            title=root_data.get("title", "Root Node"),
            node_type=NarrativeNodeType(root_data.get("node_type", "plot_point")),
            content_description=root_data.get("description", ""),
            speaker=root_data.get("speaker", ""),
        )
        graph.nodes[root.id] = root
        graph.root_node_id = root.id
        graph.total_nodes = 1

        self._graphs[graph.id] = graph
        self._graph_count += 1
        return graph

    def add_node(
        self,
        graph_id: str,
        node_type: str,
        title: str,
        description: str = "",
    ) -> str:
        graph = self._graphs.get(graph_id)
        if not graph:
            return ""

        node = NarrativeNode(
            title=title,
            node_type=NarrativeNodeType(node_type),
            content_description=description,
        )
        graph.nodes[node.id] = node
        graph.total_nodes = len(graph.nodes)

        if node.node_type == NarrativeNodeType.ENDING:
            graph.ending_count += 1

        return node.id

    def add_edge(
        self,
        graph_id: str,
        from_node: str,
        to_node: str,
        condition: Optional[Dict[str, Any]] = None,
    ) -> bool:
        graph = self._graphs.get(graph_id)
        if not graph:
            return False

        if from_node not in graph.nodes or to_node not in graph.nodes:
            return False

        parent = graph.nodes[from_node]
        if to_node not in parent.child_nodes:
            parent.child_nodes.append(to_node)
            self._edge_list.append((from_node, to_node))

        if condition:
            child = graph.nodes[to_node]
            if condition not in child.conditions:
                child.conditions.append(condition)

        self._update_graph_metrics(graph)
        return True

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        graph = self._graphs.get(graph_id)
        if not graph:
            return False

        if node_id not in graph.nodes:
            return False

        removed_node = graph.nodes[node_id]

        for node in graph.nodes.values():
            if node_id in node.child_nodes:
                node.child_nodes.remove(node_id)

        self._edge_list = [
            (f, t) for f, t in self._edge_list if f != node_id and t != node_id
        ]

        if removed_node.node_type == NarrativeNodeType.ENDING:
            graph.ending_count = max(0, graph.ending_count - 1)

        del graph.nodes[node_id]
        graph.total_nodes = len(graph.nodes)

        if graph.root_node_id == node_id and graph.nodes:
            graph.root_node_id = next(iter(graph.nodes))

        self._update_graph_metrics(graph)
        return True

    def find_path(
        self,
        graph_id: str,
        start_id: str,
        end_id: str,
    ) -> List[str]:
        graph = self._graphs.get(graph_id)
        if not graph:
            return []

        if start_id not in graph.nodes or end_id not in graph.nodes:
            return []

        if start_id == end_id:
            return [start_id]

        visited: Set[str] = set()
        queue: deque[Tuple[str, List[str]]] = deque()
        queue.append((start_id, [start_id]))
        visited.add(start_id)

        while queue:
            current, path = queue.popleft()
            node = graph.nodes[current]

            for child_id in node.child_nodes:
                if child_id == end_id:
                    return path + [child_id]
                if child_id not in visited:
                    visited.add(child_id)
                    queue.append((child_id, path + [child_id]))

        return []

    def validate_graph(self, graph_id: str) -> Dict[str, Any]:
        graph = self._graphs.get(graph_id)
        if not graph:
            return {"error": "Graph not found"}

        issues: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        if not graph.root_node_id or graph.root_node_id not in graph.nodes:
            issues.append({
                "type": "missing_root",
                "message": "Graph has no valid root node",
            })

        referenced: Set[str] = set()
        for node in graph.nodes.values():
            for child_id in node.child_nodes:
                referenced.add(child_id)

        for node_id, node in graph.nodes.items():
            if node_id != graph.root_node_id and node_id not in referenced:
                warnings.append({
                    "type": "unreachable_node",
                    "node_id": node_id,
                    "node_title": node.title,
                    "message": f"Node '{node.title}' is unreachable from root",
                })

        for node in graph.nodes.values():
            for child_id in node.child_nodes:
                if child_id not in graph.nodes:
                    issues.append({
                        "type": "dangling_reference",
                        "node_id": node.id,
                        "missing_child": child_id,
                        "message": f"Node '{node.title}' references missing child",
                    })

        ending_nodes = [
            n for n in graph.nodes.values()
            if n.node_type == NarrativeNodeType.ENDING
        ]
        if not ending_nodes:
            warnings.append({
                "type": "no_endings",
                "message": "Graph has no ending nodes defined",
            })

        leaf_count = sum(
            1 for n in graph.nodes.values() if not n.child_nodes
        )
        if leaf_count == 0:
            issues.append({
                "type": "no_leaf_nodes",
                "message": "Graph has no leaf nodes, possible infinite loop",
            })

        return {
            "graph_id": graph_id,
            "graph_title": graph.title,
            "total_nodes": graph.total_nodes,
            "issues": issues,
            "warnings": warnings,
            "is_valid": len(issues) == 0,
            "issue_count": len(issues),
            "warning_count": len(warnings),
        }

    def get_graph_stats(self, graph_id: str) -> Dict[str, Any]:
        graph = self._graphs.get(graph_id)
        if not graph:
            return {"error": "Graph not found"}

        node_type_counts: Dict[str, int] = {}
        for node in graph.nodes.values():
            ntype = node.node_type.value
            node_type_counts[ntype] = node_type_counts.get(ntype, 0) + 1

        leaf_nodes = sum(
            1 for n in graph.nodes.values() if not n.child_nodes
        )
        choice_nodes = sum(
            1 for n in graph.nodes.values() if len(n.child_nodes) > 1
        )

        return {
            "graph_id": graph_id,
            "title": graph.title,
            "total_nodes": graph.total_nodes,
            "branching_depth": graph.branching_depth,
            "ending_count": graph.ending_count,
            "leaf_nodes": leaf_nodes,
            "choice_nodes": choice_nodes,
            "node_type_distribution": node_type_counts,
            "edge_count": len(self._edge_list),
            "main_quest_length": len(graph.main_quest_line),
        }

    def add_condition(
        self,
        graph_id: str,
        node_id: str,
        condition_type: str,
        condition_data: Dict[str, Any],
    ) -> bool:
        graph = self._graphs.get(graph_id)
        if not graph or node_id not in graph.nodes:
            return False

        node = graph.nodes[node_id]
        condition = {
            "type": NarrativeCondition(condition_type).value,
            **condition_data,
        }
        node.conditions.append(condition)
        return True

    def add_impact(
        self,
        graph_id: str,
        node_id: str,
        impact_type: str,
        impact_data: Dict[str, Any],
    ) -> bool:
        graph = self._graphs.get(graph_id)
        if not graph or node_id not in graph.nodes:
            return False

        node = graph.nodes[node_id]
        impact = {
            "type": NarrativeImpact(impact_type).value,
            **impact_data,
        }
        node.impacts.append(impact)
        return True

    def get_node(self, graph_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        graph = self._graphs.get(graph_id)
        if not graph:
            return None
        node = graph.nodes.get(node_id)
        if node:
            return node.to_dict()
        return None

    def list_graphs(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self._graphs.values()]

    def _update_graph_metrics(self, graph: NarrativeGraph) -> None:
        max_depth = 0
        visited: Set[str] = set()

        def dfs(node_id: str, depth: int) -> None:
            nonlocal max_depth
            if node_id in visited:
                return
            visited.add(node_id)
            max_depth = max(max_depth, depth)
            node = graph.nodes.get(node_id)
            if node:
                for child_id in node.child_nodes:
                    dfs(child_id, depth + 1)

        if graph.root_node_id and graph.root_node_id in graph.nodes:
            dfs(graph.root_node_id, 0)

        graph.branching_depth = max_depth

        ending_nodes = [
            n for n in graph.nodes.values()
            if n.node_type == NarrativeNodeType.ENDING
        ]
        graph.ending_count = len(ending_nodes)

        if not ending_nodes:
            for node in graph.nodes.values():
                if not node.child_nodes:
                    ending_nodes.append(node)
            graph.ending_count = len(ending_nodes)

        main_line: List[str] = []
        current = graph.root_node_id
        while current and current in graph.nodes:
            main_line.append(current)
            node = graph.nodes[current]
            if not node.child_nodes:
                break
            best_child = node.child_nodes[0]
            for child_id in node.child_nodes:
                child = graph.nodes.get(child_id)
                if child and not child.is_optional:
                    best_child = child_id
                    break
            current = best_child
            if len(main_line) > 100:
                break
        graph.main_quest_line = main_line

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(g.total_nodes for g in self._graphs.values())
        total_endings = sum(g.ending_count for g in self._graphs.values())

        node_type_global: Dict[str, int] = {}
        for graph in self._graphs.values():
            for node in graph.nodes.values():
                ntype = node.node_type.value
                node_type_global[ntype] = node_type_global.get(ntype, 0) + 1

        return {
            "total_graphs": self._graph_count,
            "total_nodes": total_nodes,
            "total_edges": len(self._edge_list),
            "total_endings": total_endings,
            "node_type_distribution": node_type_global,
            "available_node_types": [t.value for t in NarrativeNodeType],
            "available_conditions": [c.value for c in NarrativeCondition],
            "available_impacts": [i.value for i in NarrativeImpact],
            "avg_nodes_per_graph": (
                total_nodes / self._graph_count if self._graph_count > 0 else 0
            ),
        }


def get_narrative_graph() -> NarrativeGraphEngine:
    return NarrativeGraphEngine.get_instance()