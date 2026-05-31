"""
SparkLabs Engine - Scene Tree System

Core scene/node tree architecture for the SparkLabs AI-native game
engine. Manages hierarchical node trees, scene definitions, node
lifecycle simulation, and scene serialization. The flat-dict node
storage with parent-child ID references enables fast lookups and
straightforward serialization without circular dependency issues.

Architecture:
  SceneTree (singleton)
    |-- SceneDefinition (scene container with flat node registry)
    |     |-- SceneNode (individual node in the tree)
    |     |-- root_node_id → SceneNode (entry point for tree traversal)
    |-- Node Lifecycle: ENTER_TREE → READY → PROCESS/PHYSICS_PROCESS → EXIT_TREE → IDLE
    |-- Node Types: 20 categorized node classifications

Usage:
    st = get_scene_tree()
    scene_id = st.create_scene("MainLevel", "The first level")
    enemy_id = st.add_node(scene_id, st._scenes[scene_id].root_node_id,
                           "Enemy", NodeType.RIGID_BODY.value, 100.0, 200.0)
    st.set_node_property(scene_id, enemy_id, "health", 100)
    tree = st.get_node_tree(scene_id)
    stats = st.get_scene_stats(scene_id)
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(Enum):
    NODE = "node"
    NODE2D = "node2d"
    NODE3D = "node3d"
    SPRITE = "sprite"
    ANIMATED_SPRITE = "animated_sprite"
    COLLISION_SHAPE = "collision_shape"
    AREA = "area"
    RIGID_BODY = "rigid_body"
    KINEMATIC_BODY = "kinematic_body"
    CAMERA = "camera"
    LIGHT = "light"
    AUDIO_STREAM_PLAYER = "audio_stream_player"
    TIMER = "timer"
    TILE_MAP = "tile_map"
    PARTICLE_EMITTER = "particle_emitter"
    LABEL = "label"
    BUTTON = "button"
    PANEL = "panel"
    PROGRESS_BAR = "progress_bar"
    CUSTOM = "custom"


class NodeLifecycle(Enum):
    ENTER_TREE = "enter_tree"
    READY = "ready"
    PROCESS = "process"
    PHYSICS_PROCESS = "physics_process"
    EXIT_TREE = "exit_tree"
    IDLE = "idle"


class SceneFormat(Enum):
    JSON = "json"
    BINARY = "binary"


@dataclass
class SceneNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Node"
    node_type: str = NodeType.NODE.value
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    position_x: float = 0.0
    position_y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    visible: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    lifecycle: str = NodeLifecycle.IDLE.value
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "position_x": self.position_x,
            "position_y": self.position_y,
            "rotation": self.rotation,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "visible": self.visible,
            "properties": dict(self.properties),
            "tags": list(self.tags),
            "lifecycle": self.lifecycle,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneNode":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", "Node"),
            node_type=data.get("node_type", NodeType.NODE.value),
            parent_id=data.get("parent_id"),
            children_ids=list(data.get("children_ids", [])),
            position_x=data.get("position_x", 0.0),
            position_y=data.get("position_y", 0.0),
            rotation=data.get("rotation", 0.0),
            scale_x=data.get("scale_x", 1.0),
            scale_y=data.get("scale_y", 1.0),
            visible=data.get("visible", True),
            properties=dict(data.get("properties", {})),
            tags=list(data.get("tags", [])),
            lifecycle=data.get("lifecycle", NodeLifecycle.IDLE.value),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class SceneDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Untitled Scene"
    root_node_id: str = ""
    nodes: Dict[str, SceneNode] = field(default_factory=dict)
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_node_id": self.root_node_id,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "description": self.description,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneDefinition":
        nodes_raw = data.get("nodes", {})
        nodes: Dict[str, SceneNode] = {}
        for nid, node_data in nodes_raw.items():
            nodes[nid] = SceneNode.from_dict(node_data)
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", "Untitled Scene"),
            root_node_id=data.get("root_node_id", ""),
            nodes=nodes,
            description=data.get("description", ""),
            created_at=data.get("created_at", time.time()),
        )


class SceneTree:
    _instance: Optional["SceneTree"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._scenes: Dict[str, SceneDefinition] = {}
        self._node_count: int = 0
        self._scene_count: int = 0
        self._active_scene_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "SceneTree":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Scene Lifecycle
    # ------------------------------------------------------------------

    def create_scene(self, name: str, description: str = "") -> str:
        with self._lock:
            root = SceneNode(
                name=f"{name}_Root",
                node_type=NodeType.NODE.value,
            )
            scene = SceneDefinition(
                name=name,
                root_node_id=root.id,
                nodes={root.id: root},
                description=description,
            )
            self._scenes[scene.id] = scene
            self._node_count += 1
            self._scene_count += 1
            if self._active_scene_id is None:
                self._active_scene_id = scene.id
            return scene.id

    def add_node(
        self,
        scene_id: str,
        parent_id: str,
        name: str,
        node_type: str = NodeType.NODE.value,
        pos_x: float = 0.0,
        pos_y: float = 0.0,
    ) -> Optional[str]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return None
            parent = scene.nodes.get(parent_id)
            if not parent:
                return None
            node = SceneNode(
                name=name,
                node_type=node_type,
                parent_id=parent_id,
                position_x=pos_x,
                position_y=pos_y,
            )
            scene.nodes[node.id] = node
            parent.children_ids.append(node.id)
            self._node_count += 1
            return node.id

    def remove_node(self, scene_id: str, node_id: str) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            node = scene.nodes.get(node_id)
            if not node:
                return False
            if node_id == scene.root_node_id:
                return False

            descendant_ids = self._collect_descendant_ids(scene, node_id)

            if node.parent_id:
                parent = scene.nodes.get(node.parent_id)
                if parent and node_id in parent.children_ids:
                    parent.children_ids.remove(node_id)

            for did in descendant_ids:
                if did in scene.nodes:
                    del scene.nodes[did]
                    self._node_count -= 1

            return True

    def _collect_descendant_ids(
        self, scene: SceneDefinition, node_id: str
    ) -> List[str]:
        ids: List[str] = [node_id]
        node = scene.nodes.get(node_id)
        if node:
            for child_id in node.children_ids:
                ids.extend(self._collect_descendant_ids(scene, child_id))
        return ids

    def get_node(self, scene_id: str, node_id: str) -> Optional[SceneNode]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return None
            return scene.nodes.get(node_id)

    def find_node_by_name(self, scene_id: str, name: str) -> Optional[SceneNode]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return None
            root = scene.nodes.get(scene.root_node_id)
            if not root:
                return None
            return self._find_by_name_dfs(scene, root.id, name)

    def _find_by_name_dfs(
        self, scene: SceneDefinition, current_id: str, name: str
    ) -> Optional[SceneNode]:
        node = scene.nodes.get(current_id)
        if not node:
            return None
        if node.name == name:
            return node
        for child_id in node.children_ids:
            found = self._find_by_name_dfs(scene, child_id, name)
            if found:
                return found
        return None

    def find_nodes_by_type(
        self, scene_id: str, node_type: str
    ) -> List[SceneNode]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return []
            result: List[SceneNode] = []
            for node in scene.nodes.values():
                if node.node_type == node_type:
                    result.append(node)
            return result

    def set_node_property(
        self, scene_id: str, node_id: str, key: str, value: Any
    ) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            node = scene.nodes.get(node_id)
            if not node:
                return False
            node.properties[key] = value
            return True

    def get_node_tree(self, scene_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return None
            root = scene.nodes.get(scene.root_node_id)
            if not root:
                return None
            return self._build_tree_dict(scene, root.id)

    def _build_tree_dict(
        self, scene: SceneDefinition, node_id: str
    ) -> Dict[str, Any]:
        node = scene.nodes.get(node_id)
        if not node:
            return {}
        return {
            "id": node.id,
            "name": node.name,
            "node_type": node.node_type,
            "position_x": node.position_x,
            "position_y": node.position_y,
            "rotation": node.rotation,
            "scale_x": node.scale_x,
            "scale_y": node.scale_y,
            "visible": node.visible,
            "properties": dict(node.properties),
            "tags": list(node.tags),
            "lifecycle": node.lifecycle,
            "children": [
                self._build_tree_dict(scene, child_id)
                for child_id in node.children_ids
            ],
        }

    def move_node(
        self, scene_id: str, node_id: str, new_parent_id: str
    ) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            node = scene.nodes.get(node_id)
            new_parent = scene.nodes.get(new_parent_id)
            if not node or not new_parent:
                return False
            if node_id == scene.root_node_id:
                return False
            if self._is_descendant(scene, node_id, new_parent_id):
                return False

            if node.parent_id:
                old_parent = scene.nodes.get(node.parent_id)
                if old_parent and node_id in old_parent.children_ids:
                    old_parent.children_ids.remove(node_id)

            node.parent_id = new_parent_id
            new_parent.children_ids.append(node_id)
            return True

    def _is_descendant(
        self, scene: SceneDefinition, ancestor_id: str, node_id: str
    ) -> bool:
        current_id = node_id
        while current_id:
            node = scene.nodes.get(current_id)
            if not node:
                return False
            if node.parent_id == ancestor_id:
                return True
            current_id = node.parent_id or ""
        return False

    def clone_subtree(
        self, scene_id: str, node_id: str
    ) -> Optional[Dict[str, str]]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return None
            node = scene.nodes.get(node_id)
            if not node:
                return None

            id_mapping: Dict[str, str] = {}
            descendant_ids = self._collect_descendant_ids(scene, node_id)

            for old_id in descendant_ids:
                id_mapping[old_id] = uuid.uuid4().hex

            for old_id in descendant_ids:
                old_node = scene.nodes.get(old_id)
                if not old_node:
                    continue
                new_id = id_mapping[old_id]
                cloned = SceneNode(
                    id=new_id,
                    name=old_node.name,
                    node_type=old_node.node_type,
                    parent_id=(
                        id_mapping.get(old_node.parent_id)
                        if old_node.parent_id and old_node.parent_id in id_mapping
                        else None
                    ),
                    children_ids=[
                        id_mapping[cid]
                        for cid in old_node.children_ids
                        if cid in id_mapping
                    ],
                    position_x=old_node.position_x,
                    position_y=old_node.position_y,
                    rotation=old_node.rotation,
                    scale_x=old_node.scale_x,
                    scale_y=old_node.scale_y,
                    visible=old_node.visible,
                    properties=dict(old_node.properties),
                    tags=list(old_node.tags),
                    lifecycle=NodeLifecycle.IDLE.value,
                )
                scene.nodes[new_id] = cloned
                self._node_count += 1

            return id_mapping

    def instantiate_scene(
        self, template_scene_id: str, target_scene_id: str, parent_id: str
    ) -> bool:
        with self._lock:
            template = self._scenes.get(template_scene_id)
            target = self._scenes.get(target_scene_id)
            if not template or not target:
                return False
            parent = target.nodes.get(parent_id)
            if not parent:
                return False

            id_mapping: Dict[str, str] = {}
            for old_id in template.nodes:
                id_mapping[old_id] = uuid.uuid4().hex

            template_root = template.nodes.get(template.root_node_id)
            mapped_root_id = id_mapping.get(template.root_node_id, "") if template_root else ""

            for old_id, old_node in template.nodes.items():
                new_id = id_mapping[old_id]
                is_root = old_id == template.root_node_id
                cloned = SceneNode(
                    id=new_id,
                    name=old_node.name,
                    node_type=old_node.node_type,
                    parent_id=(
                        parent_id if is_root
                        else id_mapping.get(old_node.parent_id)
                        if old_node.parent_id and old_node.parent_id in id_mapping
                        else None
                    ),
                    children_ids=[
                        id_mapping[cid]
                        for cid in old_node.children_ids
                        if cid in id_mapping
                    ],
                    position_x=old_node.position_x,
                    position_y=old_node.position_y,
                    rotation=old_node.rotation,
                    scale_x=old_node.scale_x,
                    scale_y=old_node.scale_y,
                    visible=old_node.visible,
                    properties=dict(old_node.properties),
                    tags=list(old_node.tags),
                    lifecycle=NodeLifecycle.IDLE.value,
                )
                target.nodes[new_id] = cloned
                self._node_count += 1

            if mapped_root_id:
                parent.children_ids.append(mapped_root_id)

            return True

    def export_scene(
        self, scene_id: str, fmt: SceneFormat = SceneFormat.JSON
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return None
            return scene.to_dict()

    def import_scene(
        self, data: Dict[str, Any], fmt: SceneFormat = SceneFormat.JSON
    ) -> Optional[str]:
        with self._lock:
            scene = SceneDefinition.from_dict(data)
            if not scene.root_node_id or scene.root_node_id not in scene.nodes:
                return None
            if scene.id in self._scenes:
                scene.id = uuid.uuid4().hex
            self._scenes[scene.id] = scene
            self._node_count += len(scene.nodes)
            self._scene_count += 1
            return scene.id

    def get_scene_stats(self, scene_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return None

            node_count = len(scene.nodes)
            type_breakdown: Dict[str, int] = {}
            for node in scene.nodes.values():
                t = node.node_type
                type_breakdown[t] = type_breakdown.get(t, 0) + 1

            root = scene.nodes.get(scene.root_node_id)
            max_depth = self._compute_max_depth(scene, root.id, 0) if root else 0

            return {
                "node_count": node_count,
                "node_type_breakdown": type_breakdown,
                "max_depth": max_depth,
            }

    def _compute_max_depth(
        self, scene: SceneDefinition, node_id: str, current_depth: int
    ) -> int:
        node = scene.nodes.get(node_id)
        if not node or not node.children_ids:
            return current_depth
        return max(
            self._compute_max_depth(scene, child_id, current_depth + 1)
            for child_id in node.children_ids
        )

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "scene_count": self._scene_count,
                "total_node_count": self._node_count,
                "active_scene": self._active_scene_id,
            }

    # ------------------------------------------------------------------
    # Lifecycle Callback Simulation
    # ------------------------------------------------------------------

    def _ready(self, scene_id: str, node_id: str) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            node = scene.nodes.get(node_id)
            if not node:
                return False
            node.lifecycle = NodeLifecycle.READY.value
            return True

    def _process(self, scene_id: str, node_id: str, delta: float) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            node = scene.nodes.get(node_id)
            if not node:
                return False
            if node.lifecycle == NodeLifecycle.IDLE.value:
                return False
            node.lifecycle = NodeLifecycle.PROCESS.value
            node.properties["_last_delta"] = delta
            node.properties["_last_process_time"] = time.time()
            return True

    def _physics_process(
        self, scene_id: str, node_id: str, delta: float
    ) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            node = scene.nodes.get(node_id)
            if not node:
                return False
            if node.lifecycle == NodeLifecycle.IDLE.value:
                return False
            node.lifecycle = NodeLifecycle.PHYSICS_PROCESS.value
            node.properties["_last_physics_delta"] = delta
            node.properties["_last_physics_time"] = time.time()
            return True


def get_scene_tree() -> SceneTree:
    return SceneTree.get_instance()