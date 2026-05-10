"""
SparkLabs Engine - Dialogue System

Branching dialogue tree engine for AI-native narrative games.
Supports conditional branching, player choices, state effects,
character portraits, localization keys, and callback hooks for
integrating dialogue with gameplay systems.

Architecture:
  DialogueSystem
    |-- DialogueTree (node graph with transitions)
    |-- DialogueNode (text, speaker, choices, effects)
    |-- ConditionEvaluator (game-state boolean logic)
    |-- EffectDispatcher (game-state mutations on choice)
    |-- ChoiceValidator (visibility filtering for options)

Features:
  - Conditional branching via game state queries
  - Choice-driven effects (inventory, stats, quests)
  - Speaker portraits and mood expressions
  - Localization-ready key-based text lookups
  - Callback hooks for custom integration
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class DialogueEffectType(Enum):
    SET_FLAG = "set_flag"
    GIVE_ITEM = "give_item"
    REMOVE_ITEM = "remove_item"
    CHANGE_STAT = "change_stat"
    START_QUEST = "start_quest"
    COMPLETE_QUEST = "complete_quest"
    TRIGGER_EVENT = "trigger_event"
    CUSTOM = "custom"


class DialogueConditionOp(Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    HAS_FLAG = "has_flag"
    HAS_ITEM = "has_item"
    QUEST_ACTIVE = "quest_active"
    QUEST_COMPLETE = "quest_complete"


@dataclass
class DialogueCondition:
    condition_type: DialogueConditionOp
    key: str
    value: Any = None

    def evaluate(self, state: Dict[str, Any]) -> bool:
        if self.condition_type == DialogueConditionOp.HAS_FLAG:
            flags: Set[str] = state.get("flags", set())
            return self.key in flags
        if self.condition_type == DialogueConditionOp.HAS_ITEM:
            items: List[str] = state.get("inventory", [])
            return self.key in items
        if self.condition_type == DialogueConditionOp.EQUALS:
            return state.get(self.key) == self.value
        if self.condition_type == DialogueConditionOp.NOT_EQUALS:
            return state.get(self.key) != self.value
        if self.condition_type == DialogueConditionOp.GREATER_THAN:
            current = state.get(self.key, 0)
            if isinstance(current, (int, float)) and isinstance(self.value, (int, float)):
                return current > self.value
            return False
        if self.condition_type == DialogueConditionOp.LESS_THAN:
            current = state.get(self.key, 0)
            if isinstance(current, (int, float)) and isinstance(self.value, (int, float)):
                return current < self.value
            return False
        if self.condition_type == DialogueConditionOp.QUEST_ACTIVE:
            active_quests: List[str] = state.get("active_quests", [])
            return self.key in active_quests
        if self.condition_type == DialogueConditionOp.QUEST_COMPLETE:
            completed: List[str] = state.get("completed_quests", [])
            return self.key in completed
        return True


@dataclass
class DialogueEffect:
    effect_type: DialogueEffectType
    key: str
    value: Any = None

    def apply(self, state: Dict[str, Any]) -> None:
        if self.effect_type == DialogueEffectType.SET_FLAG:
            state.setdefault("flags", set()).add(self.key)
        elif self.effect_type == DialogueEffectType.GIVE_ITEM:
            state.setdefault("inventory", []).append(self.key)
        elif self.effect_type == DialogueEffectType.REMOVE_ITEM:
            inv: List[str] = state.get("inventory", [])
            if self.key in inv:
                inv.remove(self.key)
        elif self.effect_type == DialogueEffectType.CHANGE_STAT:
            current = state.get(self.key, 0)
            state[self.key] = current + int(self.value)
        elif self.effect_type == DialogueEffectType.START_QUEST:
            state.setdefault("active_quests", []).append(self.key)
        elif self.effect_type == DialogueEffectType.COMPLETE_QUEST:
            active: List[str] = state.get("active_quests", [])
            if self.key in active:
                active.remove(self.key)
            state.setdefault("completed_quests", []).append(self.key)


@dataclass
class DialogueChoice:
    choice_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    text_key: str = ""
    next_node_id: str = ""
    conditions: List[DialogueCondition] = field(default_factory=list)
    effects: List[DialogueEffect] = field(default_factory=list)
    enabled: bool = True


@dataclass
class DialogueNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    speaker_name: str = ""
    portrait_id: str = ""
    text: str = ""
    text_key: str = ""
    choices: List[DialogueChoice] = field(default_factory=list)
    next_node_id: str = ""
    effects: List[DialogueEffect] = field(default_factory=list)
    conditions: List[DialogueCondition] = field(default_factory=list)
    mood: str = "neutral"
    is_terminal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueTree:
    tree_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    nodes: Dict[str, DialogueNode] = field(default_factory=dict)
    start_node_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class DialogueSystem:
    """
    Branching dialogue tree engine for narrative-driven games.
    Manages dialogue flow, condition evaluation, and effect dispatching.
    """

    _instance: Optional[DialogueSystem] = None

    @classmethod
    def get_instance(cls) -> DialogueSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._trees: Dict[str, DialogueTree] = {}
        self._active_conversations: Dict[str, str] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._conversation_count: int = 0

    def register_tree(self, tree: DialogueTree) -> str:
        self._trees[tree.tree_id] = tree
        return tree.tree_id

    def create_tree(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        start_node_id: str = "",
    ) -> str:
        tree = DialogueTree(name=name)
        for node_data in nodes:
            node_id = node_data.get("node_id", str(uuid.uuid4())[:8])
            node = DialogueNode(
                node_id=node_id,
                speaker_name=node_data.get("speaker_name", ""),
                text=node_data.get("text", ""),
                next_node_id=node_data.get("next_node_id", ""),
                is_terminal=node_data.get("is_terminal", False),
            )
            for choice_data in node_data.get("choices", []):
                choice = DialogueChoice(
                    text=choice_data.get("text", ""),
                    next_node_id=choice_data.get("next_node_id", ""),
                )
                node.choices.append(choice)
            tree.nodes[node_id] = node
        tree.start_node_id = start_node_id or (list(tree.nodes.keys())[0] if tree.nodes else "")
        self._trees[tree.tree_id] = tree
        return tree.tree_id

    def start_conversation(
        self,
        tree_id: str,
        conversation_id: str = "",
    ) -> Optional[DialogueNode]:
        tree = self._trees.get(tree_id)
        if tree is None or not tree.start_node_id:
            return None
        conv_id = conversation_id or str(uuid.uuid4())[:8]
        self._active_conversations[conv_id] = tree.start_node_id
        self._conversation_count += 1
        return tree.nodes.get(tree.start_node_id)

    def get_node(self, tree_id: str, node_id: str) -> Optional[DialogueNode]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        return tree.nodes.get(node_id)

    def select_choice(
        self,
        tree_id: str,
        current_node_id: str,
        choice_index: int,
        state: Optional[Dict[str, Any]] = None,
    ) -> Optional[DialogueNode]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None

        node = tree.nodes.get(current_node_id)
        if node is None:
            return None

        if choice_index < 0 or choice_index >= len(node.choices):
            return None

        choice = node.choices[choice_index]
        if state:
            for condition in choice.conditions:
                if not condition.evaluate(state):
                    return None

        if state:
            for effect in choice.effects:
                effect.apply(state)

        for effect in node.effects:
            if state:
                effect.apply(state)

        next_node = tree.nodes.get(choice.next_node_id)
        return next_node

    def get_available_choices(
        self,
        tree_id: str,
        node_id: str,
        state: Optional[Dict[str, Any]] = None,
    ) -> List[DialogueChoice]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return []

        node = tree.nodes.get(node_id)
        if node is None:
            return []

        if not state:
            return node.choices

        return [
            c
            for c in node.choices
            if all(cond.evaluate(state) for cond in c.conditions)
        ]

    def register_hook(self, event: str, callback: Callable) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(len(t.nodes) for t in self._trees.values())
        total_choices = sum(
            sum(len(n.choices) for n in t.nodes.values())
            for t in self._trees.values()
        )
        return {
            "dialogue_trees": len(self._trees),
            "total_nodes": total_nodes,
            "total_choices": total_choices,
            "active_conversations": len(self._active_conversations),
            "total_conversations_started": self._conversation_count,
            "registered_hooks": sum(len(v) for v in self._hooks.values()),
        }

    def reset(self) -> None:
        self._trees.clear()
        self._active_conversations.clear()
        self._hooks.clear()


_dialogue_system = DialogueSystem.get_instance()


def get_dialogue_system() -> DialogueSystem:
    return _dialogue_system