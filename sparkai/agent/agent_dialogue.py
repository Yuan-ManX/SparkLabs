"""
SparkAI Agent - Dialogue Engine

A comprehensive dialogue and narrative system for the AI-native game
engine. Manages NPC conversations, dialogue trees, story branching,
quest dialogue, and dynamic narrative generation.

Architecture:
  DialogueEngine
    |-- DialogueTree (branching conversation graph)
    |-- DialogueNode (individual dialogue entry with choices)
    |-- DialogueChoice (player choice leading to next node)
    |-- DialogueCondition (conditional branching logic)
    |-- DialogueVariable (conversation state tracking)
    |-- NarrativeArc (story arc management)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class DialogueType(Enum):
    GREETING = "greeting"
    QUEST = "quest"
    SHOP = "shop"
    LORE = "lore"
    COMBAT = "combat"
    ROMANCE = "romance"
    TUTORIAL = "tutorial"
    RANDOM = "random"
    STORY = "story"
    TRADE = "trade"


class NodeType(Enum):
    SPEECH = "speech"
    NARRATION = "narration"
    CHOICE = "choice"
    CONDITION = "condition"
    ACTION = "action"
    BRANCH = "branch"
    END = "end"
    JUMP = "jump"


class MoodType(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANGRY = "angry"
    SAD = "sad"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    CONTEMPTUOUS = "contemptuous"
    EXCITED = "excited"
    MYSTERIOUS = "mysterious"


class ArcStatus(Enum):
    SETUP = "setup"
    RISING = "rising"
    CLIMAX = "climax"
    FALLING = "falling"
    RESOLUTION = "resolution"


class ConditionOp(Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    HAS_FLAG = "has_flag"
    LACKS_FLAG = "lacks_flag"
    HAS_ITEM = "has_item"
    QUEST_STATE = "quest_state"


@dataclass
class DialogueCondition:
    variable: str = ""
    operator: ConditionOp = ConditionOp.EQ
    value: Any = None
    negate: bool = False

    def evaluate(self, variables: Dict[str, Any]) -> bool:
        current = variables.get(self.variable)
        if current is None:
            return self.operator == ConditionOp.LACKS_FLAG

        if self.operator == ConditionOp.EQ:
            result = current == self.value
        elif self.operator == ConditionOp.NEQ:
            result = current != self.value
        elif self.operator == ConditionOp.GT:
            result = current > self.value
        elif self.operator == ConditionOp.LT:
            result = current < self.value
        elif self.operator == ConditionOp.GTE:
            result = current >= self.value
        elif self.operator == ConditionOp.LTE:
            result = current <= self.value
        elif self.operator == ConditionOp.HAS_FLAG:
            result = self.value in current if isinstance(current, (list, set)) else False
        elif self.operator == ConditionOp.LACKS_FLAG:
            result = self.value not in current if isinstance(current, (list, set)) else True
        elif self.operator == ConditionOp.HAS_ITEM:
            result = self.value in current if isinstance(current, dict) else False
        elif self.operator == ConditionOp.QUEST_STATE:
            result = current == self.value
        else:
            result = False

        return not result if self.negate else result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable,
            "operator": self.operator.value,
            "value": self.value,
            "negate": self.negate,
        }


@dataclass
class DialogueAction:
    action_type: str = ""
    target: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "params": self.params,
        }


@dataclass
class DialogueChoice:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    next_node_id: str = ""
    condition: Optional[DialogueCondition] = None
    actions: List[DialogueAction] = field(default_factory=list)
    priority: int = 0
    once: bool = False
    chosen: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "next_node_id": self.next_node_id,
            "condition": self.condition.to_dict() if self.condition else None,
            "actions": [a.to_dict() for a in self.actions],
            "priority": self.priority,
            "once": self.once,
            "chosen": self.chosen,
        }


@dataclass
class DialogueNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_type: NodeType = NodeType.SPEECH
    speaker: str = ""
    text: str = ""
    mood: MoodType = MoodType.NEUTRAL
    choices: List[DialogueChoice] = field(default_factory=list)
    next_node_id: str = ""
    conditions: List[DialogueCondition] = field(default_factory=list)
    actions: List[DialogueAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "speaker": self.speaker,
            "text": self.text,
            "mood": self.mood.value,
            "choices": [c.to_dict() for c in self.choices],
            "next_node_id": self.next_node_id,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata,
            "position_x": self.position_x,
            "position_y": self.position_y,
        }


@dataclass
class DialogueVariable:
    name: str = ""
    value: Any = None
    var_type: str = "string"
    default_value: Any = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "var_type": self.var_type,
            "default_value": self.default_value,
            "description": self.description,
        }


@dataclass
class NarrativeArc:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    status: ArcStatus = ArcStatus.SETUP
    dialogue_ids: List[str] = field(default_factory=list)
    required_flags: List[str] = field(default_factory=list)
    completion_flags: List[str] = field(default_factory=list)
    priority: int = 2
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "dialogue_ids": self.dialogue_ids,
            "required_flags": self.required_flags,
            "completion_flags": self.completion_flags,
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class DialogueTree:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    dialogue_type: DialogueType = DialogueType.RANDOM
    npc_name: str = ""
    nodes: Dict[str, DialogueNode] = field(default_factory=dict)
    variables: Dict[str, DialogueVariable] = field(default_factory=dict)
    start_node_id: str = ""
    current_node_id: str = ""
    flags: Set[str] = field(default_factory=set)
    visit_count: Dict[str, int] = field(default_factory=dict)
    arc_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "dialogue_type": self.dialogue_type.value,
            "npc_name": self.npc_name,
            "node_count": len(self.nodes),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "variables": {k: v.to_dict() for k, v in self.variables.items()},
            "start_node_id": self.start_node_id,
            "current_node_id": self.current_node_id,
            "flags": list(self.flags),
            "arc_id": self.arc_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DialogueEngine:
    """
    Central dialogue and narrative system for the SparkLabs AI-native game engine.

    Manages NPC conversations, dialogue trees, story branching,
    quest dialogue, and dynamic narrative generation.
    """

    def __init__(self) -> None:
        self._trees: Dict[str, DialogueTree] = {}
        self._arcs: Dict[str, NarrativeArc] = {}
        self._tree_count: int = 0
        self._arc_count: int = 0
        self._conversation_count: int = 0
        self._seed_dialogues()

    def _seed_dialogues(self) -> None:
        greeting_tree = DialogueTree(
            name="Village Elder Greeting",
            description="The village elder greets the player for the first time",
            dialogue_type=DialogueType.GREETING,
            npc_name="Elder Mira",
        )

        start = DialogueNode(
            id="start",
            node_type=NodeType.SPEECH,
            speaker="Elder Mira",
            text="Welcome, traveler. I have been expecting you. The village needs your help.",
            mood=MoodType.MYSTERIOUS,
            choices=[
                DialogueChoice(id="c1", text="What kind of help?", next_node_id="quest_info", priority=1),
                DialogueChoice(id="c2", text="Who told you I was coming?", next_node_id="mystery", priority=2),
                DialogueChoice(id="c3", text="I am just passing through.", next_node_id="dismiss", priority=3),
            ],
            position_x=100,
            position_y=100,
        )

        quest_info = DialogueNode(
            id="quest_info",
            node_type=NodeType.SPEECH,
            speaker="Elder Mira",
            text="A darkness spreads from the ancient tower to the north. Our warriors cannot approach it. Only an outsider might succeed where we have failed.",
            mood=MoodType.SAD,
            choices=[
                DialogueChoice(id="c4", text="I will help.", next_node_id="accept",
                    actions=[DialogueAction("set_flag", "quest_tower_accepted", {"flag": "tower_quest"})]),
                DialogueChoice(id="c5", text="Tell me more first.", next_node_id="lore"),
            ],
            position_x=350,
            position_y=50,
        )

        mystery = DialogueNode(
            id="mystery",
            node_type=NodeType.SPEECH,
            speaker="Elder Mira",
            text="The stars speak to those who listen. And they spoke your name.",
            mood=MoodType.MYSTERIOUS,
            next_node_id="quest_info",
            position_x=350,
            position_y=200,
        )

        dismiss = DialogueNode(
            id="dismiss",
            node_type=NodeType.END,
            speaker="Elder Mira",
            text="Very well. But if you change your mind, I will be here. The darkness will not wait forever.",
            mood=MoodType.SAD,
            position_x=350,
            position_y=350,
        )

        lore = DialogueNode(
            id="lore",
            node_type=NodeType.NARRATION,
            speaker="",
            text="The ancient tower was once a beacon of light, built by the Archon Council centuries ago. When the last Archon fell, the tower's crystal shattered, and shadow crept in.",
            mood=MoodType.NEUTRAL,
            next_node_id="quest_info",
            position_x=600,
            position_y=100,
        )

        accept = DialogueNode(
            id="accept",
            node_type=NodeType.END,
            speaker="Elder Mira",
            text="Thank you, brave one. Take this amulet — it will protect you from the worst of the darkness. The tower lies north, beyond the Whispering Woods.",
            mood=MoodType.HAPPY,
            actions=[DialogueAction("give_item", "player", {"item": "shadow_amulet"})],
            position_x=600,
            position_y=250,
        )

        for node in [start, quest_info, mystery, dismiss, lore, accept]:
            greeting_tree.nodes[node.id] = node
        greeting_tree.start_node_id = "start"

        self._trees[greeting_tree.id] = greeting_tree
        self._tree_count += 1

        shop_tree = DialogueTree(
            name="Blacksmith Trade",
            description="The village blacksmith offers weapons and armor",
            dialogue_type=DialogueType.SHOP,
            npc_name="Bron Ironforge",
        )

        shop_start = DialogueNode(
            id="start",
            node_type=NodeType.SPEECH,
            speaker="Bron Ironforge",
            text="Looking for quality steel? You have come to the right place.",
            mood=MoodType.NEUTRAL,
            choices=[
                DialogueChoice(id="s1", text="Show me your weapons.", next_node_id="weapons"),
                DialogueChoice(id="s2", text="Do you have any armor?", next_node_id="armor"),
                DialogueChoice(id="s3", text="Just browsing.", next_node_id="browse_end"),
            ],
            position_x=100,
            position_y=100,
        )

        weapons = DialogueNode(
            id="weapons",
            node_type=NodeType.END,
            speaker="Bron Ironforge",
            text="I have swords, axes, and maces. The finest steel in the region.",
            mood=MoodType.EXCITED,
            actions=[DialogueAction("open_shop", "player", {"category": "weapons"})],
            position_x=350,
            position_y=50,
        )

        armor = DialogueNode(
            id="armor",
            node_type=NodeType.END,
            speaker="Bron Ironforge",
            text="Chainmail, plate, and leather — I craft them all. What is your preference?",
            mood=MoodType.NEUTRAL,
            actions=[DialogueAction("open_shop", "player", {"category": "armor"})],
            position_x=350,
            position_y=200,
        )

        browse_end = DialogueNode(
            id="browse_end",
            node_type=NodeType.END,
            speaker="Bron Ironforge",
            text="Come back when you need something. My forge is always hot.",
            mood=MoodType.NEUTRAL,
            position_x=350,
            position_y=350,
        )

        for node in [shop_start, weapons, armor, browse_end]:
            shop_tree.nodes[node.id] = node
        shop_tree.start_node_id = "start"

        self._trees[shop_tree.id] = shop_tree
        self._tree_count += 1

        main_arc = NarrativeArc(
            name="The Shadow Tower",
            description="The main story arc about the spreading darkness from the ancient tower",
            status=ArcStatus.SETUP,
            dialogue_ids=[greeting_tree.id],
            required_flags=[],
            completion_flags=["tower_quest_completed"],
            priority=1,
        )
        self._arcs[main_arc.id] = main_arc
        self._arc_count += 1

    def create_tree(
        self,
        name: str,
        dialogue_type: str = "random",
        npc_name: str = "",
        description: str = "",
    ) -> DialogueTree:
        tree = DialogueTree(
            name=name,
            description=description,
            dialogue_type=DialogueType(dialogue_type),
            npc_name=npc_name,
        )
        start_node = DialogueNode(
            id="start",
            node_type=NodeType.SPEECH,
            speaker=npc_name,
            text="...",
            mood=MoodType.NEUTRAL,
            position_x=100,
            position_y=100,
        )
        tree.nodes["start"] = start_node
        tree.start_node_id = "start"
        self._trees[tree.id] = tree
        self._tree_count += 1
        return tree

    def get_tree(self, tree_id: str) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if tree:
            return tree.to_dict()
        return None

    def list_trees(
        self,
        dialogue_type: Optional[DialogueType] = None,
        npc_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        trees = list(self._trees.values())
        if dialogue_type:
            trees = [t for t in trees if t.dialogue_type == dialogue_type]
        if npc_name:
            trees = [t for t in trees if t.npc_name == npc_name]
        return [t.to_dict() for t in trees]

    def delete_tree(self, tree_id: str) -> bool:
        if tree_id in self._trees:
            del self._trees[tree_id]
            self._tree_count -= 1
            return True
        return False

    def add_node(
        self,
        tree_id: str,
        node_type: str = "speech",
        speaker: str = "",
        text: str = "",
        mood: str = "neutral",
        next_node_id: str = "",
        position_x: float = 0.0,
        position_y: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        node = DialogueNode(
            node_type=NodeType(node_type),
            speaker=speaker,
            text=text,
            mood=MoodType(mood),
            next_node_id=next_node_id,
            position_x=position_x,
            position_y=position_y,
        )
        tree.nodes[node.id] = node
        tree.updated_at = time.time()
        return node.to_dict()

    def update_node(
        self,
        tree_id: str,
        node_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        node = tree.nodes.get(node_id)
        if not node:
            return None

        if "text" in updates:
            node.text = updates["text"]
        if "speaker" in updates:
            node.speaker = updates["speaker"]
        if "mood" in updates:
            node.mood = MoodType(updates["mood"])
        if "node_type" in updates:
            node.node_type = NodeType(updates["node_type"])
        if "next_node_id" in updates:
            node.next_node_id = updates["next_node_id"]
        if "position_x" in updates:
            node.position_x = updates["position_x"]
        if "position_y" in updates:
            node.position_y = updates["position_y"]

        tree.updated_at = time.time()
        return node.to_dict()

    def remove_node(self, tree_id: str, node_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if not tree or node_id == "start":
            return False

        if node_id in tree.nodes:
            del tree.nodes[node_id]
            for node in tree.nodes.values():
                if node.next_node_id == node_id:
                    node.next_node_id = ""
                node.choices = [c for c in node.choices if c.next_node_id != node_id]
            tree.updated_at = time.time()
            return True
        return False

    def add_choice(
        self,
        tree_id: str,
        node_id: str,
        text: str,
        next_node_id: str = "",
        priority: int = 0,
        once: bool = False,
    ) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        node = tree.nodes.get(node_id)
        if not node:
            return None

        choice = DialogueChoice(
            text=text,
            next_node_id=next_node_id,
            priority=priority,
            once=once,
        )
        node.choices.append(choice)
        tree.updated_at = time.time()
        return choice.to_dict()

    def remove_choice(self, tree_id: str, node_id: str, choice_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if not tree:
            return False

        node = tree.nodes.get(node_id)
        if not node:
            return False

        before = len(node.choices)
        node.choices = [c for c in node.choices if c.id != choice_id]
        if len(node.choices) < before:
            tree.updated_at = time.time()
            return True
        return False

    def advance_dialogue(
        self,
        tree_id: str,
        choice_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        if not tree.current_node_id:
            tree.current_node_id = tree.start_node_id
            self._conversation_count += 1
            current = tree.nodes.get(tree.current_node_id)
            if current:
                tree.visit_count[current.id] = tree.visit_count.get(current.id, 0) + 1
                return {
                    "node": current.to_dict(),
                    "flags": list(tree.flags),
                    "conversation_id": tree_id,
                }
            return None

        current = tree.nodes.get(tree.current_node_id)
        if not current:
            return None

        tree.visit_count[current.id] = tree.visit_count.get(current.id, 0) + 1

        if choice_id:
            chosen = None
            for choice in current.choices:
                if choice.id == choice_id:
                    chosen = choice
                    break

            if not chosen:
                return {"error": f"Choice '{choice_id}' not found"}

            chosen.chosen = True

            for action in chosen.actions:
                if action.action_type == "set_flag":
                    flag = action.params.get("flag", action.target)
                    tree.flags.add(flag)
                elif action.action_type == "set_variable":
                    var_name = action.params.get("variable", action.target)
                    var_value = action.params.get("value")
                    if var_name in tree.variables:
                        tree.variables[var_name].value = var_value

            next_id = chosen.next_node_id
        else:
            next_id = current.next_node_id

        if next_id and next_id in tree.nodes:
            next_node = tree.nodes[next_id]
            for cond in next_node.conditions:
                if not cond.evaluate({k: v.value for k, v in tree.variables.items()}):
                    return {"blocked": True, "reason": f"Condition not met: {cond.variable}"}

            for action in next_node.actions:
                if action.action_type == "set_flag":
                    flag = action.params.get("flag", action.target)
                    tree.flags.add(flag)

            tree.current_node_id = next_id
            return {
                "node": next_node.to_dict(),
                "flags": list(tree.flags),
                "conversation_id": tree_id,
            }
        else:
            tree.current_node_id = ""
            return {"ended": True, "conversation_id": tree_id}

    def reset_dialogue(self, tree_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if not tree:
            return False
        tree.current_node_id = ""
        tree.flags.clear()
        for var in tree.variables.values():
            var.value = var.default_value
        for node in tree.nodes.values():
            for choice in node.choices:
                choice.chosen = False
        return True

    def add_variable(
        self,
        tree_id: str,
        name: str,
        var_type: str = "string",
        default_value: Any = None,
        description: str = "",
    ) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        var = DialogueVariable(
            name=name,
            value=default_value,
            var_type=var_type,
            default_value=default_value,
            description=description,
        )
        tree.variables[name] = var
        return var.to_dict()

    def set_variable(self, tree_id: str, name: str, value: Any) -> bool:
        tree = self._trees.get(tree_id)
        if not tree or name not in tree.variables:
            return False
        tree.variables[name].value = value
        return True

    def create_arc(
        self,
        name: str,
        description: str = "",
        priority: int = 2,
    ) -> NarrativeArc:
        arc = NarrativeArc(
            name=name,
            description=description,
            priority=priority,
        )
        self._arcs[arc.id] = arc
        self._arc_count += 1
        return arc

    def get_arc(self, arc_id: str) -> Optional[Dict[str, Any]]:
        arc = self._arcs.get(arc_id)
        if arc:
            return arc.to_dict()
        return None

    def list_arcs(self, status: Optional[ArcStatus] = None) -> List[Dict[str, Any]]:
        arcs = list(self._arcs.values())
        if status:
            arcs = [a for a in arcs if a.status == status]
        return [a.to_dict() for a in arcs]

    def update_arc_status(self, arc_id: str, status: str) -> Optional[Dict[str, Any]]:
        arc = self._arcs.get(arc_id)
        if not arc:
            return None
        arc.status = ArcStatus(status)
        return arc.to_dict()

    def link_dialogue_to_arc(self, arc_id: str, tree_id: str) -> bool:
        arc = self._arcs.get(arc_id)
        if not arc:
            return False
        if tree_id not in arc.dialogue_ids:
            arc.dialogue_ids.append(tree_id)
        return True

    def get_stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for tree in self._trees.values():
            key = tree.dialogue_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        total_nodes = sum(len(t.nodes) for t in self._trees.values())
        total_choices = sum(
            sum(len(n.choices) for n in t.nodes.values())
            for t in self._trees.values()
        )

        return {
            "total_trees": self._tree_count,
            "total_arcs": self._arc_count,
            "total_conversations": self._conversation_count,
            "total_nodes": total_nodes,
            "total_choices": total_choices,
            "by_type": type_counts,
        }


_global_dialogue_engine: Optional[DialogueEngine] = None


def get_dialogue_engine() -> DialogueEngine:
    global _global_dialogue_engine
    if _global_dialogue_engine is None:
        _global_dialogue_engine = DialogueEngine()
    return _global_dialogue_engine
