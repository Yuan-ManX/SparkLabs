"""
SparkLabs Engine - Animation Tree Runtime

Animation blending state machine providing weighted transitions between
animation clips and layered animation compositing for simultaneous
body-part animations on skeletal and sprite-based characters.

Architecture:
  AnimationTreeRuntime
    |-- BlendTree (directed acyclic graph of animation nodes and transitions)
    |-- AnimationNode (nodes with input/output poses and blend parameters)
    |-- AnimationClip (keyframe data with timing and interpolation)
    |-- Transition (rule-based movement between animation nodes with easing)
    |-- AnimationLayer (composited pose layers with blend masks and weights)
"""
from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BlendMode(Enum):
    LINEAR = "linear"
    CUBIC = "cubic"
    STEP = "step"
    ADDITIVE = "additive"


class TreePlayMode(Enum):
    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    CLAMP = "clamp"


class TransitionCondition(Enum):
    TIME = "time"
    PARAMETER = "parameter"
    EVENT = "event"
    EXPRESSION = "expression"


class LayerBlendMode(Enum):
    MIX = "mix"
    ADD = "add"
    MASK = "mask"


@dataclass
class AnimationClip:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    duration: float = 1.0
    fps: float = 30.0
    keyframes: List[Dict[str, Any]] = field(default_factory=list)
    total_frames: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "duration": round(self.duration, 3),
            "fps": round(self.fps, 1),
            "keyframes": len(self.keyframes),
            "total_frames": self.total_frames,
        }


@dataclass
class AnimationNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    clip_id: str = ""
    parent_id: str = ""
    children: List[str] = field(default_factory=list)
    blend_mode: BlendMode = BlendMode.LINEAR
    weight: float = 1.0
    play_mode: TreePlayMode = TreePlayMode.LOOP
    speed: float = 1.0
    local_time: float = 0.0
    is_active: bool = False
    blend_parameters: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "clip_id": self.clip_id,
            "parent_id": self.parent_id, "children": list(self.children),
            "blend_mode": self.blend_mode.value,
            "weight": round(self.weight, 3),
            "play_mode": self.play_mode.value, "speed": self.speed,
            "local_time": round(self.local_time, 3),
            "is_active": self.is_active,
            "blend_parameters": dict(self.blend_parameters),
        }


@dataclass
class BlendTree:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    skeleton_ref: str = ""
    root_node_id: str = ""
    nodes: Dict[str, AnimationNode] = field(default_factory=dict)
    clips: Dict[str, AnimationClip] = field(default_factory=dict)
    layers: Dict[str, AnimationLayer] = field(default_factory=dict)
    transitions: Dict[str, Dict[str, Transition]] = field(default_factory=dict)
    is_playing: bool = False
    current_time: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "skeleton_ref": self.skeleton_ref,
            "root_node_id": self.root_node_id,
            "node_count": len(self.nodes), "clip_count": len(self.clips),
            "layer_count": len(self.layers),
            "transition_count": sum(len(t) for t in self.transitions.values()),
            "is_playing": self.is_playing,
            "current_time": round(self.current_time, 3),
            "created_at": self.created_at,
        }


@dataclass
class Transition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_node_id: str = ""
    to_node_id: str = ""
    condition_type: TransitionCondition = TransitionCondition.TIME
    duration: float = 0.3
    condition_params: Dict[str, Any] = field(default_factory=dict)
    ease_in: float = 0.0
    ease_out: float = 0.0
    priority: int = 0
    elapsed: float = 0.0
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "condition_type": self.condition_type.value,
            "duration": self.duration,
            "condition_params": self.condition_params,
            "ease_in": self.ease_in, "ease_out": self.ease_out,
            "priority": self.priority,
            "elapsed": round(self.elapsed, 3), "is_active": self.is_active,
        }


@dataclass
class AnimationLayer:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tree_id: str = ""
    blend_mode: LayerBlendMode = LayerBlendMode.MIX
    weight: float = 1.0
    mask_bones: List[str] = field(default_factory=list)
    is_enabled: bool = True
    sort_order: int = 0
    node_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "tree_id": self.tree_id,
            "blend_mode": self.blend_mode.value,
            "weight": round(self.weight, 3),
            "mask_bones": list(self.mask_bones),
            "is_enabled": self.is_enabled, "sort_order": self.sort_order,
            "node_id": self.node_id,
        }


class AnimationTreeRuntime:
    """Animation blending state machine with layered pose compositing."""

    _instance: Optional["AnimationTreeRuntime"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._trees: Dict[str, BlendTree] = {}
        self._blend_parameters: Dict[str, Dict[str, float]] = {}
        self._baked_clips: Dict[str, AnimationClip] = {}

    @classmethod
    def get_instance(cls) -> "AnimationTreeRuntime":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Tree Management ----

    def create_tree(self, name: str, skeleton_ref: str = "") -> BlendTree:
        tree = BlendTree(name=name, skeleton_ref=skeleton_ref)
        self._trees[tree.id] = tree
        self._blend_parameters[tree.id] = {}
        return tree

    def add_clip(self, tree_id: str, name: str,
                 keyframes: Optional[List[Dict[str, Any]]] = None,
                 duration: float = 1.0, fps: float = 30.0) -> Optional[AnimationClip]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        kf = keyframes or [{"frame": i, "pose": {}}
                           for i in range(max(1, int(duration * fps)))]
        clip = AnimationClip(name=name, duration=duration, fps=fps,
                             keyframes=kf, total_frames=len(kf))
        tree.clips[clip.id] = clip
        return clip

    def create_blend_node(self, tree_id: str, parent_id: str = "",
                          blend_mode: str = "linear") -> Optional[AnimationNode]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        try:
            bm = BlendMode(blend_mode.lower())
        except ValueError:
            bm = BlendMode.LINEAR
        node = AnimationNode(name=f"BlendNode_{len(tree.nodes)}",
                             parent_id=parent_id, blend_mode=bm)
        tree.nodes[node.id] = node
        if parent_id and parent_id in tree.nodes:
            tree.nodes[parent_id].children.append(node.id)
        if not tree.root_node_id:
            tree.root_node_id = node.id
        return node

    def add_transition(self, from_node_id: str, to_node_id: str,
                       condition_type: str = "time", duration: float = 0.3,
                       condition_params: Optional[Dict[str, Any]] = None
                       ) -> Optional[Transition]:
        try:
            ct = TransitionCondition(condition_type.lower())
        except ValueError:
            ct = TransitionCondition.TIME
        transition = Transition(
            from_node_id=from_node_id, to_node_id=to_node_id,
            condition_type=ct, duration=duration,
            condition_params=condition_params or {})
        for tree in self._trees.values():
            if from_node_id in tree.nodes:
                tree.transitions.setdefault(from_node_id, {})[to_node_id] = transition
                return transition
        return None

    def create_layer(self, tree_id: str, name: str,
                     blend_mode: str = "mix",
                     weight: float = 1.0) -> Optional[AnimationLayer]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        try:
            lbm = LayerBlendMode(blend_mode.lower())
        except ValueError:
            lbm = LayerBlendMode.MIX
        layer = AnimationLayer(name=name, tree_id=tree_id, blend_mode=lbm,
                               weight=max(0.0, min(1.0, weight)),
                               sort_order=len(tree.layers))
        tree.layers[layer.id] = layer
        return layer

    # ---- Parameter Control ----

    def set_blend_parameter(self, tree_id: str, param_name: str, value: float) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None:
            return False
        self._blend_parameters.setdefault(tree_id, {})[param_name] = value
        return True

    # ---- Playback Control ----

    def play(self, tree_id: str, start_node_id: str = "") -> Dict[str, Any]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return {"error": "Tree not found", "success": False}
        if start_node_id and start_node_id in tree.nodes:
            tree.root_node_id = start_node_id
        tree.is_playing = True
        tree.current_time = 0.0
        root = tree.nodes.get(tree.root_node_id)
        if root:
            root.is_active = True
            root.local_time = 0.0
        return {"success": True, "tree_id": tree_id, "tree_name": tree.name}

    def pause(self, tree_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None:
            return False
        tree.is_playing = False
        return True

    def stop(self, tree_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None:
            return False
        tree.is_playing = False
        tree.current_time = 0.0
        for node in tree.nodes.values():
            node.is_active = False
            node.local_time = 0.0
        return True

    # ---- Pose Computation ----

    def compute_pose(self, tree_id: str,
                     delta_time: float = 0.016) -> Dict[str, Any]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return {"error": "Tree not found", "pose": {}}
        if not tree.is_playing:
            return {"pose": {}, "tree_id": tree_id, "is_playing": False}
        tree.current_time += delta_time
        root = tree.nodes.get(tree.root_node_id)
        if root is None:
            return {"pose": {}, "tree_id": tree_id, "is_playing": True}
        root.local_time += delta_time * root.speed
        self._process_transitions(tree, delta_time)
        pose = self._evaluate_node(tree, root)
        return {
            "pose": self._composite_layers(tree, pose),
            "tree_id": tree_id, "tree_name": tree.name,
            "current_time": tree.current_time,
            "active_nodes": [nid for nid, n in tree.nodes.items() if n.is_active],
            "is_playing": True,
        }

    def _evaluate_node(self, tree: BlendTree, node: AnimationNode) -> Dict[str, Any]:
        clip = tree.clips.get(node.clip_id)
        if node.blend_mode == BlendMode.STEP:
            return self._sample_clip(clip, node, 1.0)

        children = []
        for child_id in node.children:
            child = tree.nodes.get(child_id)
            if child and child.is_active:
                children.append((self._evaluate_node(tree, child), child.weight))

        own = self._sample_clip(clip, node, node.weight)
        if not children:
            return own

        result = dict(own)
        total = node.weight + sum(w for _, w in children)
        if total <= 0:
            return result

        for child_pose, cw in children:
            if node.blend_mode == BlendMode.ADDITIVE:
                for bone, xforms in child_pose.items():
                    if bone in result:
                        for k in xforms:
                            if k in result[bone]:
                                result[bone][k] += xforms[k] * cw
            elif node.blend_mode == BlendMode.CUBIC:
                t = cw / total
                st = t * t * (3.0 - 2.0 * t)
                for bone, xforms in child_pose.items():
                    if bone in result:
                        for k in xforms:
                            if k in result[bone]:
                                result[bone][k] += (xforms[k] - result[bone][k]) * st
            else:
                norm = cw / total
                for bone, xforms in child_pose.items():
                    if bone in result:
                        for k in xforms:
                            if k in result[bone]:
                                result[bone][k] = (result[bone][k] * (1.0 - norm)
                                                   + xforms[k] * norm)
        return result

    def _sample_clip(self, clip: Optional[AnimationClip],
                     node: AnimationNode, weight: float) -> Dict[str, Any]:
        if clip is None:
            return {}
        if node.play_mode == TreePlayMode.ONCE:
            if node.local_time >= clip.duration:
                node.local_time = clip.duration
                node.is_active = False
        elif node.play_mode == TreePlayMode.LOOP:
            node.local_time %= clip.duration
        elif node.play_mode == TreePlayMode.PING_PONG:
            cycle = node.local_time / max(0.001, clip.duration)
            node.local_time = abs((cycle % 2.0) - 1.0) * clip.duration
        elif node.play_mode == TreePlayMode.CLAMP:
            node.local_time = max(0.0, min(node.local_time, clip.duration))
        fi = int(node.local_time * clip.fps) % max(1, clip.total_frames)
        pose = dict(clip.keyframes[fi].get("pose", {})) if clip.keyframes and fi < len(clip.keyframes) else {}
        for bone in pose:
            for k in pose[bone]:
                if isinstance(pose[bone][k], (int, float)):
                    pose[bone][k] *= weight
        return pose

    def _process_transitions(self, tree: BlendTree, dt: float) -> None:
        for from_id, targets in tree.transitions.items():
            from_node = tree.nodes.get(from_id)
            for to_id, trans in targets.items():
                if trans.is_active:
                    trans.elapsed += dt
                    if trans.elapsed >= trans.duration:
                        trans.is_active = False
                        trans.elapsed = 0.0
                        if from_node:
                            from_node.is_active = False
                        to_node = tree.nodes.get(to_id)
                        if to_node:
                            to_node.is_active = True
                            to_node.local_time = 0.0
                    continue
                if not from_node or not from_node.is_active:
                    continue
                if self._check_transition(tree, trans):
                    trans.is_active = True
                    trans.elapsed = 0.0
                    to_node = tree.nodes.get(to_id)
                    if to_node:
                        to_node.is_active = True
                        to_node.local_time = 0.0

    def _check_transition(self, tree: BlendTree, trans: Transition) -> bool:
        params = self._blend_parameters.get(tree.id, {})
        ct = trans.condition_type
        if ct == TransitionCondition.TIME:
            return tree.current_time >= trans.condition_params.get("after_seconds", 0.0)
        if ct == TransitionCondition.PARAMETER:
            name = trans.condition_params.get("name", "")
            target = trans.condition_params.get("value", 0.0)
            op = trans.condition_params.get("op", "gte")
            cur = params.get(name, 0.0)
            if op == "gte":
                return cur >= target
            if op == "lte":
                return cur <= target
            if op == "eq":
                return abs(cur - target) < 0.001
            return cur >= target
        if ct == TransitionCondition.EVENT:
            queued = trans.condition_params.get("_queued", False)
            if queued:
                trans.condition_params["_queued"] = False
                return True
            return False
        if ct == TransitionCondition.EXPRESSION:
            expr = trans.condition_params.get("expression", "")
            if expr:
                try:
                    return bool(eval(expr, {"__builtins__": {}},
                                     {"params": params, "time": tree.current_time}))
                except Exception:
                    pass
        return False

    def _composite_layers(self, tree: BlendTree,
                          base_pose: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base_pose)
        for layer in sorted(
                [l for l in tree.layers.values() if l.is_enabled],
                key=lambda l: l.sort_order):
            ln = tree.nodes.get(layer.node_id)
            if ln is None or not ln.is_active:
                continue
            lp = self._evaluate_node(tree, ln)
            for bone, xforms in lp.items():
                if layer.blend_mode == LayerBlendMode.MASK:
                    if layer.mask_bones and bone not in layer.mask_bones:
                        continue
                if bone not in result:
                    result[bone] = {}
                if layer.blend_mode == LayerBlendMode.ADD:
                    for k in xforms:
                        if k in result[bone]:
                            result[bone][k] += xforms[k] * layer.weight
                        else:
                            result[bone][k] = xforms[k] * layer.weight
                else:
                    for k in xforms:
                        r = result[bone].get(k, 0.0)
                        result[bone][k] = r * (1.0 - layer.weight) + xforms[k] * layer.weight
        return result

    # ---- Animation Baking ----

    def bake_animation(self, tree_id: str,
                       target_clip_name: str = "") -> Optional[AnimationClip]:
        tree = self._trees.get(tree_id)
        if tree is None or not tree.root_node_id:
            return None
        was_playing, orig_time = tree.is_playing, tree.current_time
        orig_states = {nid: (n.local_time, n.is_active) for nid, n in tree.nodes.items()}
        duration = max(1.0, max((c.duration for c in tree.clips.values()), default=1.0))
        frames = int(duration * 30)
        tree.is_playing, tree.current_time = True, 0.0
        root = tree.nodes.get(tree.root_node_id)
        if root:
            root.is_active, root.local_time = True, 0.0
        baked = [self.compute_pose(tree_id, delta_time=1.0/30) for _ in range(frames)]
        kfs = [{"frame": i, "time": round(i/30.0, 3), "pose": b.get("pose", {})}
               for i, b in enumerate(baked)]
        tree.is_playing, tree.current_time = was_playing, orig_time
        for nid, (lt, act) in orig_states.items():
            n = tree.nodes.get(nid)
            if n:
                n.local_time, n.is_active = lt, act
        clip = AnimationClip(name=target_clip_name or f"{tree.name}_baked",
                             duration=duration, fps=30, keyframes=kfs, total_frames=frames)
        self._baked_clips[clip.id] = clip
        return clip

    # ---- Access and Stats ----

    def get_tree(self, tree_id: str) -> Optional[BlendTree]:
        return self._trees.get(tree_id)

    def list_trees(self) -> List[BlendTree]:
        return list(self._trees.values())

    def get_stats(self) -> Dict[str, Any]:
        nodes = sum(len(t.nodes) for t in self._trees.values())
        return {
            "total_trees": len(self._trees),
            "playing_trees": sum(1 for t in self._trees.values() if t.is_playing),
            "total_nodes": nodes,
            "total_clips": sum(len(t.clips) for t in self._trees.values()),
            "total_layers": sum(len(t.layers) for t in self._trees.values()),
            "total_transitions": sum(
                sum(len(x) for x in t.transitions.values())
                for t in self._trees.values()),
            "baked_clips": len(self._baked_clips),
        }


def get_animation_tree() -> AnimationTreeRuntime:
    return AnimationTreeRuntime.get_instance()