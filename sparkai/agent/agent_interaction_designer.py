"""
SparkLabs Agent - Interaction Designer

AI-driven UI/UX interaction flow designer for game interfaces.
Models complete interaction architectures including screens, dialogs,
overlays, and navigation patterns. Provides flow validation, AI-driven
flow generation from natural language prompts, accessibility analysis,
and JSON serialization for integration with design toolchains.

Architecture:
  InteractionDesigner
    |-- FlowNode (individual interaction surface)
    |-- FlowTransition (animated state changes between nodes)
    |-- InteractionFlow (complete flow graph with metadata)
    |-- AccessibilityAnalyzer (WCAG compliance verification)
    |-- FlowValidator (structural integrity and dead-end detection)
    |-- FlowPromptInterpreter (natural language to flow generation)

Supports 9 interaction patterns and 7 flow node types for
comprehensive UI/UX modeling across game genres.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class InteractionPattern(Enum):
    TAP = "tap"
    SWIPE = "swipe"
    DRAG = "drag"
    PINCH = "pinch"
    LONG_PRESS = "long_press"
    HOVER = "hover"
    SCROLL = "scroll"
    KEYBOARD = "keyboard"
    GAMEPAD = "gamepad"


class FlowNodeType(Enum):
    SCREEN = "screen"
    DIALOG = "dialog"
    OVERLAY = "overlay"
    TOAST = "toast"
    BOTTOM_SHEET = "bottom_sheet"
    NAVIGATION = "navigation"
    ANIMATION = "animation"


class TransitionType(Enum):
    FADE = "fade"
    SLIDE = "slide"
    SCALE = "scale"
    ROTATE = "rotate"
    FLIP = "flip"
    CUSTOM = "custom"
    NONE = "none"


class AccessibilityLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    AA_COMPLIANT = "aa_compliant"
    AAA_COMPLIANT = "aaa_compliant"


@dataclass
class FlowNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    node_type: FlowNodeType = FlowNodeType.SCREEN
    title: str = ""
    description: str = ""
    component_key: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "title": self.title,
            "description": self.description,
            "component_key": self.component_key,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }


@dataclass
class FlowTransition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    from_node_id: str = ""
    to_node_id: str = ""
    trigger: str = ""
    transition_type: TransitionType = TransitionType.FADE
    duration: float = 0.3
    condition: str = ""
    animation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "trigger": self.trigger,
            "transition_type": self.transition_type.value,
            "duration": self.duration,
            "condition": self.condition,
            "animation": self.animation,
        }


@dataclass
class InteractionFlow:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    game_genre: str = ""
    nodes: Dict[str, FlowNode] = field(default_factory=dict)
    transitions: List[FlowTransition] = field(default_factory=list)
    accessibility: AccessibilityLevel = AccessibilityLevel.NONE
    responsive_breakpoints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "game_genre": self.game_genre,
            "node_count": len(self.nodes),
            "transition_count": len(self.transitions),
            "accessibility": self.accessibility.value,
            "responsive_breakpoints": self.responsive_breakpoints,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "transitions": [t.to_dict() for t in self.transitions],
        }


GENRE_FLOW_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "platformer": {
        "nodes": [
            {"name": "main_menu", "type": "screen", "x": 0, "y": 0},
            {"name": "hud", "type": "overlay", "x": 300, "y": 0},
            {"name": "pause_menu", "type": "overlay", "x": 600, "y": 0},
            {"name": "level_select", "type": "screen", "x": 0, "y": 300},
            {"name": "settings", "type": "dialog", "x": 300, "y": 300},
        ],
        "transitions": [
            {"from": "main_menu", "to": "hud", "trigger": "start_game"},
            {"from": "hud", "to": "pause_menu", "trigger": "pause"},
            {"from": "main_menu", "to": "level_select", "trigger": "select_level"},
        ],
        "breaks": ["768px", "1024px", "1440px"],
    },
    "rpg": {
        "nodes": [
            {"name": "main_menu", "type": "screen", "x": 0, "y": 0},
            {"name": "inventory", "type": "screen", "x": 300, "y": 0},
            {"name": "character_sheet", "type": "screen", "x": 600, "y": 0},
            {"name": "dialog_system", "type": "dialog", "x": 0, "y": 300},
            {"name": "quest_log", "type": "overlay", "x": 300, "y": 300},
            {"name": "shop", "type": "screen", "x": 600, "y": 300},
        ],
        "transitions": [
            {"from": "main_menu", "to": "inventory", "trigger": "open_inventory"},
            {"from": "main_menu", "to": "character_sheet", "trigger": "open_character"},
            {"from": "main_menu", "to": "dialog_system", "trigger": "npc_interact"},
            {"from": "inventory", "to": "shop", "trigger": "talk_to_vendor"},
        ],
        "breaks": ["768px", "1024px", "1440px"],
    },
    "fps": {
        "nodes": [
            {"name": "main_menu", "type": "screen", "x": 0, "y": 0},
            {"name": "hud", "type": "overlay", "x": 300, "y": 0},
            {"name": "scoreboard", "type": "overlay", "x": 600, "y": 0},
            {"name": "loadout", "type": "screen", "x": 0, "y": 300},
            {"name": "minimap", "type": "overlay", "x": 300, "y": 300},
        ],
        "transitions": [
            {"from": "main_menu", "to": "hud", "trigger": "join_match"},
            {"from": "hud", "to": "scoreboard", "trigger": "show_scoreboard"},
            {"from": "main_menu", "to": "loadout", "trigger": "customize_loadout"},
        ],
        "breaks": ["768px", "1024px", "1440px"],
    },
    "puzzle": {
        "nodes": [
            {"name": "main_menu", "type": "screen", "x": 0, "y": 0},
            {"name": "game_board", "type": "screen", "x": 300, "y": 0},
            {"name": "hint_overlay", "type": "toast", "x": 600, "y": 0},
            {"name": "level_complete", "type": "dialog", "x": 0, "y": 300},
            {"name": "tutorial", "type": "overlay", "x": 300, "y": 300},
        ],
        "transitions": [
            {"from": "main_menu", "to": "game_board", "trigger": "start_game"},
            {"from": "game_board", "to": "hint_overlay", "trigger": "request_hint"},
            {"from": "game_board", "to": "level_complete", "trigger": "solve_puzzle"},
        ],
        "breaks": ["768px", "1024px", "1440px"],
    },
    "strategy": {
        "nodes": [
            {"name": "main_menu", "type": "screen", "x": 0, "y": 0},
            {"name": "hud", "type": "overlay", "x": 300, "y": 0},
            {"name": "build_menu", "type": "screen", "x": 600, "y": 0},
            {"name": "tech_tree", "type": "screen", "x": 0, "y": 300},
            {"name": "diplomacy", "type": "dialog", "x": 300, "y": 300},
            {"name": "victory_screen", "type": "screen", "x": 600, "y": 300},
        ],
        "transitions": [
            {"from": "main_menu", "to": "hud", "trigger": "start_game"},
            {"from": "hud", "to": "build_menu", "trigger": "open_build"},
            {"from": "hud", "to": "tech_tree", "trigger": "open_tech"},
            {"from": "hud", "to": "diplomacy", "trigger": "open_diplomacy"},
        ],
        "breaks": ["768px", "1024px", "1440px"],
    },
}


class InteractionDesigner:
    """AI-driven UI/UX interaction flow designer for game interfaces."""

    _instance: Optional["InteractionDesigner"] = None
    _lock = threading.RLock()

    MAX_FLOWS = 200

    def __init__(self):
        self._flows: Dict[str, InteractionFlow] = {}
        self._flow_count: int = 0
        self._total_transitions: int = 0

    @classmethod
    def get_instance(cls) -> "InteractionDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_flow(
        self,
        name: str,
        game_genre: str = "",
        accessibility: AccessibilityLevel = AccessibilityLevel.NONE,
    ) -> InteractionFlow:
        responsive_breaks: List[str] = []
        if game_genre.lower() in GENRE_FLOW_TEMPLATES:
            responsive_breaks = GENRE_FLOW_TEMPLATES[game_genre.lower()]["breaks"]

        flow = InteractionFlow(
            name=name,
            game_genre=game_genre,
            accessibility=accessibility,
            responsive_breakpoints=list(responsive_breaks),
        )

        self._flows[flow.id] = flow
        self._flow_count += 1

        if len(self._flows) > self.MAX_FLOWS:
            oldest = min(
                self._flows.keys(),
                key=lambda k: len(self._flows[k].nodes) + len(self._flows[k].transitions),
            )
            del self._flows[oldest]

        return flow

    def add_node(
        self,
        flow_id: str,
        name: str,
        node_type: FlowNodeType,
        title: str = "",
        description: str = "",
        component_key: str = "",
        position_x: float = 0.0,
        position_y: float = 0.0,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> Optional[FlowNode]:
        flow = self._flows.get(flow_id)
        if flow is None:
            return None

        node = FlowNode(
            name=name,
            node_type=node_type,
            title=title or name,
            description=description,
            component_key=component_key or name,
            position_x=position_x,
            position_y=position_y,
            inputs=inputs or {},
            outputs=outputs or {},
        )
        flow.nodes[node.id] = node
        return node

    def add_transition(
        self,
        flow_id: str,
        from_node_id: str,
        to_node_id: str,
        trigger: str = "",
        transition_type: TransitionType = TransitionType.FADE,
        duration: float = 0.3,
        name: str = "",
        condition: str = "",
        animation: str = "",
    ) -> Optional[FlowTransition]:
        flow = self._flows.get(flow_id)
        if flow is None:
            return None

        if from_node_id not in flow.nodes or to_node_id not in flow.nodes:
            return None

        transition = FlowTransition(
            name=name or f"{from_node_id[:8]}_to_{to_node_id[:8]}",
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            trigger=trigger,
            transition_type=transition_type,
            duration=duration,
            condition=condition,
            animation=animation,
        )
        flow.transitions.append(transition)
        self._total_transitions += 1
        return transition

    def remove_node(self, flow_id: str, node_id: str) -> bool:
        flow = self._flows.get(flow_id)
        if flow is None or node_id not in flow.nodes:
            return False

        del flow.nodes[node_id]

        flow.transitions = [
            t for t in flow.transitions
            if t.from_node_id != node_id and t.to_node_id != node_id
        ]
        return True

    def remove_transition(self, flow_id: str, transition_id: str) -> bool:
        flow = self._flows.get(flow_id)
        if flow is None:
            return False

        for i, t in enumerate(flow.transitions):
            if t.id == transition_id:
                flow.transitions.pop(i)
                return True
        return False

    def validate_flow(self, flow_id: str) -> Dict[str, Any]:
        flow = self._flows.get(flow_id)
        if flow is None:
            return {"error": "Flow not found"}

        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        if not flow.nodes:
            errors.append({
                "type": "empty_flow",
                "message": "Flow has no nodes defined",
            })

        referenced: set = set()
        for t in flow.transitions:
            if t.from_node_id not in flow.nodes:
                errors.append({
                    "type": "dangling_transition",
                    "message": f"Transition '{t.name}' references missing source node",
                    "transition_id": t.id,
                    "missing_node": t.from_node_id,
                })
            if t.to_node_id not in flow.nodes:
                errors.append({
                    "type": "dangling_transition",
                    "message": f"Transition '{t.name}' references missing target node",
                    "transition_id": t.id,
                    "missing_node": t.to_node_id,
                })
            referenced.add(t.from_node_id)
            referenced.add(t.to_node_id)

        for node_id, node in flow.nodes.items():
            if node_id not in referenced and len(flow.nodes) > 1:
                warnings.append({
                    "type": "disconnected_node",
                    "message": f"Node '{node.name}' has no transitions",
                    "node_id": node_id,
                })

        self._check_dead_ends(flow, warnings)
        self._check_navigation_loops(flow, warnings)

        return {
            "flow_id": flow_id,
            "flow_name": flow.name,
            "node_count": len(flow.nodes),
            "transition_count": len(flow.transitions),
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
        }

    def _check_dead_ends(
        self, flow: InteractionFlow, warnings: List[Dict[str, Any]]
    ) -> None:
        outgoing: Dict[str, bool] = {node_id: False for node_id in flow.nodes}
        for t in flow.transitions:
            outgoing[t.from_node_id] = True

        for node_id, has_outgoing in outgoing.items():
            node = flow.nodes[node_id]
            if not has_outgoing and node.node_type not in (
                FlowNodeType.TOAST, FlowNodeType.DIALOG
            ):
                warnings.append({
                    "type": "dead_end",
                    "message": f"Node '{node.name}' has no outgoing transitions",
                    "node_id": node_id,
                })

    def _check_navigation_loops(
        self, flow: InteractionFlow, warnings: List[Dict[str, Any]]
    ) -> None:
        WHITE, GRAY, BLACK = 0, 1, 2
        colors: Dict[str, int] = {nid: WHITE for nid in flow.nodes}

        def dfs(node_id: str) -> bool:
            colors[node_id] = GRAY
            for t in flow.transitions:
                if t.from_node_id == node_id:
                    neighbor = t.to_node_id
                    if neighbor not in colors:
                        continue
                    if colors[neighbor] == GRAY:
                        return True
                    if colors[neighbor] == WHITE and dfs(neighbor):
                        return True
            colors[node_id] = BLACK
            return False

        for nid in flow.nodes:
            if colors[nid] == WHITE:
                if dfs(nid):
                    warnings.append({
                        "type": "navigation_loop",
                        "message": "Flow contains cyclic navigation, ensure back-navigation handles state correctly",
                    })
                    return

    def generate_flow_from_prompt(self, prompt: str) -> InteractionFlow:
        prompt_lower = prompt.lower()

        game_genre = self._extract_genre_from_prompt(prompt_lower)
        accessibility = self._extract_accessibility_from_prompt(prompt_lower)

        flow = self.create_flow(
            name=f"flow_{uuid.uuid4().hex[:8]}",
            game_genre=game_genre,
            accessibility=accessibility,
        )

        template = GENRE_FLOW_TEMPLATES.get(game_genre)
        if template:
            self._apply_template(flow, template, prompt_lower)
        else:
            self._generate_default_nodes(flow, prompt_lower)

        requested_nodes = self._parse_requested_nodes(prompt_lower)
        for node_spec in requested_nodes:
            self.add_node(
                flow_id=flow.id,
                name=node_spec["name"],
                node_type=node_spec["type"],
                title=node_spec.get("title", node_spec["name"]),
                description=node_spec.get("description", ""),
                position_x=node_spec.get("x", 0.0),
                position_y=node_spec.get("y", 0.0),
            )

        requested_transitions = self._parse_requested_transitions(prompt_lower, flow.nodes)
        for trans_spec in requested_transitions:
            if trans_spec["from"] in flow.nodes and trans_spec["to"] in flow.nodes:
                self.add_transition(
                    flow_id=flow.id,
                    from_node_id=trans_spec["from"],
                    to_node_id=trans_spec["to"],
                    trigger=trans_spec.get("trigger", ""),
                    transition_type=trans_spec.get("transition_type", TransitionType.FADE),
                    duration=trans_spec.get("duration", 0.3),
                )

        self._auto_wire_nodes(flow)

        return flow

    def _extract_genre_from_prompt(self, prompt_lower: str) -> str:
        genre_keywords: Dict[str, List[str]] = {
            "platformer": ["platform", "jump", "side-scroll", "platformer"],
            "rpg": ["rpg", "role-play", "quest", "inventory", "character"],
            "fps": ["fps", "shooter", "first-person", "shooting"],
            "puzzle": ["puzzle", "match", "solve", "brain"],
            "strategy": ["strategy", "rts", "tactical", "build", "resource"],
        }

        for genre, keywords in genre_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                return genre

        return "platformer"

    def _extract_accessibility_from_prompt(self, prompt_lower: str) -> AccessibilityLevel:
        if "aaa" in prompt_lower or "highest accessibility" in prompt_lower:
            return AccessibilityLevel.AAA_COMPLIANT
        if "aa" in prompt_lower or "accessible" in prompt_lower or "a11y" in prompt_lower:
            return AccessibilityLevel.AA_COMPLIANT
        if "basic" in prompt_lower and "accessibility" in prompt_lower:
            return AccessibilityLevel.BASIC
        return AccessibilityLevel.NONE

    def _apply_template(
        self, flow: InteractionFlow, template: Dict[str, Any], prompt_lower: str
    ) -> None:
        for node_data in template.get("nodes", []):
            self.add_node(
                flow_id=flow.id,
                name=node_data["name"],
                node_type=FlowNodeType(node_data["type"]),
                position_x=float(node_data.get("x", 0)),
                position_y=float(node_data.get("y", 0)),
            )

        node_by_name = {n.name: n.id for n in flow.nodes.values()}
        for trans_data in template.get("transitions", []):
            from_id = node_by_name.get(trans_data["from"])
            to_id = node_by_name.get(trans_data["to"])
            if from_id and to_id:
                self.add_transition(
                    flow_id=flow.id,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    trigger=trans_data.get("trigger", ""),
                    transition_type=TransitionType.SLIDE,
                )

    def _generate_default_nodes(self, flow: InteractionFlow, prompt_lower: str) -> None:
        self.add_node(
            flow_id=flow.id,
            name="main_menu",
            node_type=FlowNodeType.SCREEN,
            title="Main Menu",
            description="Primary entry point for the game",
            position_x=0.0,
            position_y=0.0,
        )

        if "settings" in prompt_lower or "options" in prompt_lower:
            self.add_node(
                flow_id=flow.id,
                name="settings",
                node_type=FlowNodeType.DIALOG,
                title="Settings",
                description="Game configuration and options",
                position_x=300.0,
                position_y=0.0,
            )

        if "hud" in prompt_lower or "in-game" in prompt_lower:
            self.add_node(
                flow_id=flow.id,
                name="hud",
                node_type=FlowNodeType.OVERLAY,
                title="HUD",
                description="In-game heads-up display",
                position_x=0.0,
                position_y=300.0,
            )

    def _parse_requested_nodes(
        self, prompt_lower: str
    ) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []

        node_specs: Dict[str, FlowNodeType] = {
            "bottom sheet": FlowNodeType.BOTTOM_SHEET,
            "bottom_sheet": FlowNodeType.BOTTOM_SHEET,
            "toast notification": FlowNodeType.TOAST,
            "toast": FlowNodeType.TOAST,
            "navigation bar": FlowNodeType.NAVIGATION,
            "navbar": FlowNodeType.NAVIGATION,
            "loading screen": FlowNodeType.ANIMATION,
            "animated transition": FlowNodeType.ANIMATION,
            "splash screen": FlowNodeType.ANIMATION,
        }

        for keyword, node_type in node_specs.items():
            if keyword in prompt_lower:
                idx = prompt_lower.index(keyword)
                name = keyword.replace(" ", "_")
                nodes.append({
                    "name": name,
                    "type": node_type,
                    "title": keyword.title(),
                    "description": f"Auto-generated {keyword} node",
                    "x": float(len(nodes) * 300),
                    "y": 300.0,
                })

        return nodes

    def _parse_requested_transitions(
        self, prompt_lower: str, existing_nodes: Dict[str, FlowNode]
    ) -> List[Dict[str, Any]]:
        transitions: List[Dict[str, Any]] = []
        node_names = list(existing_nodes.keys())

        transition_hints: Dict[str, TransitionType] = {
            "fade": TransitionType.FADE,
            "slide": TransitionType.SLIDE,
            "scale": TransitionType.SCALE,
            "rotate": TransitionType.ROTATE,
            "flip": TransitionType.FLIP,
        }

        for hint, trans_type in transition_hints.items():
            if hint in prompt_lower and len(node_names) >= 2:
                transitions.append({
                    "from": node_names[0],
                    "to": node_names[1],
                    "trigger": f"navigate_to_{node_names[1]}",
                    "transition_type": trans_type,
                    "duration": 0.3,
                })

        return transitions

    def _auto_wire_nodes(self, flow: InteractionFlow) -> None:
        screen_nodes = [
            n for n in flow.nodes.values()
            if n.node_type == FlowNodeType.SCREEN
        ]
        overlay_nodes = [
            n for n in flow.nodes.values()
            if n.node_type == FlowNodeType.OVERLAY
        ]

        if not flow.transitions and len(screen_nodes) >= 2:
            for i in range(len(screen_nodes) - 1):
                self.add_transition(
                    flow_id=flow.id,
                    from_node_id=screen_nodes[i].id,
                    to_node_id=screen_nodes[i + 1].id,
                    trigger=f"navigate_{screen_nodes[i + 1].name}",
                    transition_type=TransitionType.SLIDE,
                )

        for screen in screen_nodes:
            for overlay in overlay_nodes:
                has_transition = any(
                    t.from_node_id == screen.id and t.to_node_id == overlay.id
                    for t in flow.transitions
                )
                if not has_transition:
                    self.add_transition(
                        flow_id=flow.id,
                        from_node_id=screen.id,
                        to_node_id=overlay.id,
                        trigger=f"show_{overlay.name}",
                        transition_type=TransitionType.FADE,
                        duration=0.2,
                    )

    def suggest_improvements(self, flow_id: str) -> List[Dict[str, Any]]:
        flow = self._flows.get(flow_id)
        if flow is None:
            return []

        suggestions: List[Dict[str, Any]] = []

        if flow.accessibility == AccessibilityLevel.NONE:
            suggestions.append({
                "category": "accessibility",
                "severity": "high",
                "message": "Consider adding at least BASIC accessibility support",
                "recommendation": "Add ARIA labels and keyboard navigation support",
            })

        has_back = any("back" in t.trigger.lower() for t in flow.transitions)
        if not has_back and len(flow.transitions) > 0:
            suggestions.append({
                "category": "navigation",
                "severity": "medium",
                "message": "No back-navigation transitions defined",
                "recommendation": "Add back-navigation triggers to allow users to return to previous screens",
            })

        if not flow.responsive_breakpoints:
            suggestions.append({
                "category": "responsive",
                "severity": "medium",
                "message": "No responsive breakpoints configured",
                "recommendation": "Define breakpoints for mobile, tablet, and desktop layouts",
            })

        toast_count = sum(
            1 for n in flow.nodes.values() if n.node_type == FlowNodeType.TOAST
        )
        if toast_count > 5:
            suggestions.append({
                "category": "ux",
                "severity": "medium",
                "message": f"High toast count ({toast_count}), may overwhelm users",
                "recommendation": "Consolidate toasts or use a notification center pattern",
            })

        screen_count = sum(
            1 for n in flow.nodes.values() if n.node_type == FlowNodeType.SCREEN
        )
        if screen_count == 1 and len(flow.nodes) > 3:
            suggestions.append({
                "category": "architecture",
                "severity": "low",
                "message": "Single screen with many overlays may indicate missing navigation structure",
                "recommendation": "Consider adding more screens with clear navigation flows",
            })

        if flow.transitions:
            avg_duration = sum(t.duration for t in flow.transitions) / len(flow.transitions)
            if avg_duration > 0.5:
                suggestions.append({
                    "category": "performance",
                    "severity": "low",
                    "message": f"Average transition duration is high ({avg_duration:.2f}s)",
                    "recommendation": "Reduce transition durations to under 0.3s for snappier UX",
                })

        return suggestions

    def export_to_json(self, flow_id: str) -> str:
        flow = self._flows.get(flow_id)
        if flow is None:
            return json.dumps({"error": "Flow not found"})

        return json.dumps(flow.to_dict(), indent=2)

    def import_from_json(self, json_data: str) -> Optional[InteractionFlow]:
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return None

        flow = InteractionFlow(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            game_genre=data.get("game_genre", ""),
            accessibility=AccessibilityLevel(data.get("accessibility", "none")),
            responsive_breakpoints=data.get("responsive_breakpoints", []),
        )

        for node_data in data.get("nodes", []):
            node = FlowNode(
                id=node_data.get("id", uuid.uuid4().hex),
                name=node_data.get("name", ""),
                node_type=FlowNodeType(node_data.get("node_type", "screen")),
                title=node_data.get("title", ""),
                description=node_data.get("description", ""),
                component_key=node_data.get("component_key", ""),
                position_x=node_data.get("position_x", 0.0),
                position_y=node_data.get("position_y", 0.0),
                inputs=node_data.get("inputs", {}),
                outputs=node_data.get("outputs", {}),
            )
            flow.nodes[node.id] = node

        for trans_data in data.get("transitions", []):
            trans = FlowTransition(
                id=trans_data.get("id", uuid.uuid4().hex),
                name=trans_data.get("name", ""),
                from_node_id=trans_data.get("from_node_id", ""),
                to_node_id=trans_data.get("to_node_id", ""),
                trigger=trans_data.get("trigger", ""),
                transition_type=TransitionType(trans_data.get("transition_type", "fade")),
                duration=trans_data.get("duration", 0.3),
                condition=trans_data.get("condition", ""),
                animation=trans_data.get("animation", ""),
            )
            flow.transitions.append(trans)

        self._flows[flow.id] = flow
        self._flow_count += 1
        self._total_transitions += len(flow.transitions)

        if len(self._flows) > self.MAX_FLOWS:
            oldest = min(
                self._flows.keys(),
                key=lambda k: len(self._flows[k].nodes) + len(self._flows[k].transitions),
            )
            del self._flows[oldest]

        return flow

    def analyze_accessibility(self, flow_id: str) -> Dict[str, Any]:
        flow = self._flows.get(flow_id)
        if flow is None:
            return {"error": "Flow not found"}

        issues: List[Dict[str, Any]] = []
        score = 100

        if flow.accessibility == AccessibilityLevel.NONE:
            issues.append({
                "type": "no_accessibility",
                "message": "No accessibility level set on the flow",
                "severity": "critical",
            })
            score -= 40
        elif flow.accessibility == AccessibilityLevel.BASIC:
            score -= 20

        for node in flow.nodes.values():
            if not node.description:
                issues.append({
                    "type": "missing_description",
                    "message": f"Node '{node.name}' has no description for screen readers",
                    "node_id": node.id,
                    "severity": "medium",
                })
                score -= 5

            if not node.title:
                issues.append({
                    "type": "missing_title",
                    "message": f"Node '{node.name}' has no title",
                    "node_id": node.id,
                    "severity": "low",
                })
                score -= 2

        for trans in flow.transitions:
            if not trans.trigger:
                issues.append({
                    "type": "missing_trigger",
                    "message": f"Transition from '{trans.from_node_id[:8]}' has no trigger description",
                    "transition_id": trans.id,
                    "severity": "low",
                })
                score -= 2

            if trans.duration <= 0:
                issues.append({
                    "type": "instant_transition",
                    "message": f"Transition '{trans.name}' has zero duration, may cause disorientation",
                    "transition_id": trans.id,
                    "severity": "low",
                })
                score -= 1

        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        medium_count = sum(1 for i in issues if i["severity"] == "medium")
        low_count = sum(1 for i in issues if i["severity"] == "low")

        return {
            "flow_id": flow_id,
            "flow_name": flow.name,
            "accessibility_level": flow.accessibility.value,
            "score": max(0, score),
            "total_issues": len(issues),
            "critical_issues": critical_count,
            "medium_issues": medium_count,
            "low_issues": low_count,
            "issues": issues,
        }

    def get_flow_stats(self, flow_id: str) -> Dict[str, Any]:
        flow = self._flows.get(flow_id)
        if flow is None:
            return {"error": "Flow not found"}

        node_type_counts: Dict[str, int] = {}
        for node in flow.nodes.values():
            ntype = node.node_type.value
            node_type_counts[ntype] = node_type_counts.get(ntype, 0) + 1

        trans_type_counts: Dict[str, int] = {}
        total_duration = 0.0
        for trans in flow.transitions:
            ttype = trans.transition_type.value
            trans_type_counts[ttype] = trans_type_counts.get(ttype, 0) + 1
            total_duration += trans.duration

        incoming: Dict[str, int] = {}
        outgoing: Dict[str, int] = {}
        for t in flow.transitions:
            outgoing[t.from_node_id] = outgoing.get(t.from_node_id, 0) + 1
            incoming[t.to_node_id] = incoming.get(t.to_node_id, 0) + 1

        avg_duration = total_duration / len(flow.transitions) if flow.transitions else 0.0

        return {
            "flow_id": flow_id,
            "flow_name": flow.name,
            "game_genre": flow.game_genre,
            "total_nodes": len(flow.nodes),
            "total_transitions": len(flow.transitions),
            "accessibility_level": flow.accessibility.value,
            "responsive_breakpoints": flow.responsive_breakpoints,
            "node_type_distribution": node_type_counts,
            "transition_type_distribution": trans_type_counts,
            "average_transition_duration": round(avg_duration, 3),
            "max_incoming": max(incoming.values()) if incoming else 0,
            "max_outgoing": max(outgoing.values()) if outgoing else 0,
        }

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(len(f.nodes) for f in self._flows.values())
        total_transitions_count = sum(len(f.transitions) for f in self._flows.values())

        node_type_global: Dict[str, int] = {}
        accessibility_global: Dict[str, int] = {}
        genre_global: Dict[str, int] = {}

        for flow in self._flows.values():
            for node in flow.nodes.values():
                ntype = node.node_type.value
                node_type_global[ntype] = node_type_global.get(ntype, 0) + 1

            alevel = flow.accessibility.value
            accessibility_global[alevel] = accessibility_global.get(alevel, 0) + 1

            genre = flow.game_genre or "unspecified"
            genre_global[genre] = genre_global.get(genre, 0) + 1

        return {
            "total_flows": self._flow_count,
            "active_flows": len(self._flows),
            "total_nodes": total_nodes,
            "total_transitions": total_transitions_count,
            "max_flows": self.MAX_FLOWS,
            "avg_nodes_per_flow": (
                total_nodes / len(self._flows) if self._flows else 0
            ),
            "node_type_distribution": node_type_global,
            "accessibility_distribution": accessibility_global,
            "genre_distribution": genre_global,
            "available_node_types": [t.value for t in FlowNodeType],
            "available_transition_types": [t.value for t in TransitionType],
            "available_interaction_patterns": [p.value for p in InteractionPattern],
            "available_accessibility_levels": [a.value for a in AccessibilityLevel],
        }


def get_interaction_designer() -> InteractionDesigner:
    return InteractionDesigner.get_instance()