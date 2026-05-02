"""
Node Path System - Path-based node query and resolution for the scene tree.

Architecture:
    NodePathSystem/
    |-- PathComponent (single path segment dataclass)
    |-- NodePath (parsed path expression dataclass)
    |-- PathQuery (filter criteria dataclass)
    |-- NodePathSystem (global path orchestration)

Implements a path expression language for navigating the scene tree hierarchy.
Supports absolute paths (/root/child), relative paths (./sibling, ../parent),
wildcard selection (//enemies/*), and filter-based node querying. Essential
for AI-generated games where the agent references objects by path.
"""

from __future__ import annotations

import uuid
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PathSegmentType(Enum):
    ROOT = auto()
    CHILD = auto()
    PARENT = auto()
    SELF = auto()
    NAME = auto()
    WILDCARD = auto()
    RECURSIVE = auto()
    FILTER = auto()


@dataclass
class PathComponent:
    segment_type: PathSegmentType = PathSegmentType.NAME
    name: str = ""
    filter_attr: str = ""
    filter_value: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.segment_type.name,
            "name": self.name,
        }


@dataclass
class NodePath:
    path_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original: str = ""
    components: List[PathComponent] = field(default_factory=list)
    is_absolute: bool = False

    def resolve(self, current_node: Any, root: Any) -> List[Any]:
        if self.is_absolute and root:
            context = root
        else:
            context = current_node

        result = [context]
        for comp in self.components:
            result = self._resolve_component(result, comp)

        return result

    def _resolve_component(self, contexts: List[Any], comp: PathComponent) -> List[Any]:
        results = []

        if comp.segment_type == PathSegmentType.WILDCARD:
            for ctx in contexts:
                children = self._get_children(ctx)
                results.extend(children)

        elif comp.segment_type == PathSegmentType.RECURSIVE:
            for ctx in contexts:
                results.extend(self._recursive_collect(ctx))
                children = self._get_children(ctx)
                results.extend(children)

        elif comp.segment_type == PathSegmentType.PARENT:
            for ctx in contexts:
                parent = self._get_parent(ctx)
                if parent:
                    results.append(parent)

        elif comp.segment_type == PathSegmentType.SELF:
            results = list(contexts)

        elif comp.segment_type == PathSegmentType.FILTER:
            for ctx in contexts:
                attr_val = self._get_attribute(ctx, comp.filter_attr)
                if str(attr_val) == comp.filter_value:
                    results.append(ctx)

        else:
            for ctx in contexts:
                children = self._get_children(ctx)
                for child in children:
                    name = self._get_node_name(child)
                    if name == comp.name:
                        results.append(child)

        return results

    def _get_children(self, node: Any) -> List[Any]:
        if hasattr(node, 'get_children'):
            return node.get_children()
        if hasattr(node, 'children') and isinstance(node.children, list):
            return node.children
        return []

    def _get_parent(self, node: Any) -> Optional[Any]:
        if hasattr(node, 'get_parent'):
            return node.get_parent()
        if hasattr(node, 'parent'):
            return node.parent
        return None

    def _get_node_name(self, node: Any) -> str:
        if hasattr(node, 'name'):
            return getattr(node, 'name')
        if isinstance(node, dict) and 'name' in node:
            return node['name']
        return str(node)

    def _get_attribute(self, node: Any, attr: str) -> Any:
        if hasattr(node, attr):
            return getattr(node, attr)
        if isinstance(node, dict) and attr in node:
            return node[attr]
        return None

    def _recursive_collect(self, node: Any) -> List[Any]:
        results = []
        children = self._get_children(node)
        for child in children:
            results.append(child)
            results.extend(self._recursive_collect(child))
        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "original": self.original,
            "is_absolute": self.is_absolute,
            "component_count": len(self.components),
            "components": [c.to_dict() for c in self.components],
        }


@dataclass
class PathQuery:
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: NodePath = field(default_factory=NodePath)
    node_type: str = ""
    limit: int = 100
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "path": self.path.original,
            "node_type": self.node_type,
            "limit": self.limit,
        }


class NodePathSystem:
    _instance: Optional["NodePathSystem"] = None

    _PATH_PATTERN = re.compile(
        r'(\.\.|\.|/|//|[*])|([A-Za-z_][A-Za-z0-9_]*)'
        r'|\[([A-Za-z_][A-Za-z0-9_]*)=(.*?)\]'
    )

    def __init__(self):
        self._paths: Dict[str, NodePath] = {}
        self._aliases: Dict[str, str] = {}
        self._query_count: int = 0

    @classmethod
    def get_instance(cls) -> "NodePathSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def parse(self, path_str: str) -> NodePath:
        components = []
        is_absolute = path_str.startswith("/")
        working = path_str

        if is_absolute:
            components.append(PathComponent(segment_type=PathSegmentType.ROOT))
            working = working[1:]

        tokens = self._PATH_PATTERN.findall(working)
        i = 0
        while i < len(tokens):
            token = tokens[i]
            spec, name, fattr, fval = token

            if spec == "/":
                components.append(PathComponent(
                    segment_type=PathSegmentType.CHILD, name=name))
            elif spec == "//":
                components.append(PathComponent(segment_type=PathSegmentType.RECURSIVE))
            elif spec == "..":
                components.append(PathComponent(segment_type=PathSegmentType.PARENT))
            elif spec == ".":
                components.append(PathComponent(segment_type=PathSegmentType.SELF))
            elif spec == "*":
                components.append(PathComponent(segment_type=PathSegmentType.WILDCARD))
            elif name:
                if fattr:
                    components.append(PathComponent(
                        segment_type=PathSegmentType.FILTER,
                        filter_attr=fattr,
                        filter_value=fval.strip('"\' '),
                    ))
                else:
                    components.append(PathComponent(
                        segment_type=PathSegmentType.NAME,
                        name=name,
                    ))
            i += 1

        node_path = NodePath(
            original=path_str,
            components=components,
            is_absolute=is_absolute,
        )
        self._paths[node_path.path_id] = node_path
        return node_path

    def resolve(self, path_str: str, current: Any, root: Any) -> List[Any]:
        path = self.parse(path_str)
        self._query_count += 1
        return path.resolve(current, root)

    def resolve_one(self, path_str: str, current: Any, root: Any) -> Optional[Any]:
        results = self.resolve(path_str, current, root)
        return results[0] if results else None

    def register_alias(self, alias: str, path: str) -> None:
        self._aliases[alias] = path

    def resolve_alias(self, alias: str, current: Any, root: Any) -> List[Any]:
        path = self._aliases.get(alias)
        if not path:
            return []
        return self.resolve(path, current, root)

    def search_by_name(self, root: Any, name: str, recursive: bool = True) -> List[Any]:
        if recursive:
            path_str = f"//{name}"
        else:
            path_str = f"./{name}"
        return self.resolve(path_str, root, root)

    def search_by_type(self, root: Any, node_type: str) -> List[Any]:
        path_str = f"//[{node_type}]"
        return self.resolve(path_str, root, root)

    def list_aliases(self) -> Dict[str, str]:
        return dict(self._aliases)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "path_count": len(self._paths),
            "alias_count": len(self._aliases),
            "query_count": self._query_count,
            "aliases": self._aliases,
        }


def get_node_path_system() -> NodePathSystem:
    return NodePathSystem.get_instance()
