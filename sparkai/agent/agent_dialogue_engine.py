"""
SparkLabs Agent - Dialogue Engine

Context-aware dialogue generation system for dynamic NPC conversations.
Generates branching dialogue trees, personality-driven responses,
and context-sensitive conversation flows.

Architecture:
  AgentDialogueEngine (Singleton)
    |-- Dialogue Tree Builder (branching conversation structures)
    |-- Response Generator (personality-driven response creation)
    |-- Context Tracker (conversation history and state)
    |-- Tone Analyzer (emotional tone and sentiment detection)
    |-- Choice Generator (player dialogue options)
    |-- Conversation Memory (persistent conversation history)
    |-- Locale Adapter (language and cultural adaptation)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class DialogueTone(Enum):
    FRIENDLY = "friendly"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    SARCASTIC = "sarcastic"
    FORMAL = "formal"
    CASUAL = "casual"
    MYSTERIOUS = "mysterious"
    ENTHUSIASTIC = "enthusiastic"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    ROMANTIC = "romantic"


class DialogueNodeType(Enum):
    NPC_LINE = "npc_line"
    PLAYER_CHOICE = "player_choice"
    BRANCH = "branch"
    CONDITION = "condition"
    GREETING = "greeting"
    FAREWELL = "farewell"
    QUEST_RELATED = "quest_related"
    LORE = "lore"
    TRADE = "trade"
    RUMOR = "rumor"


class ConversationMood(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    TENSE = "tense"
    CURIOUS = "curious"
    AMUSED = "amused"


@dataclass
class DialogueLine:
    """A single line of dialogue in a conversation."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    speaker_id: str = ""
    speaker_name: str = ""
    text: str = ""
    tone: DialogueTone = DialogueTone.NEUTRAL
    node_type: DialogueNodeType = DialogueNodeType.NPC_LINE
    emotion_tags: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)
    parent_id: str = ""
    is_terminal: bool = False
    order_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "text": self.text,
            "tone": self.tone.value,
            "node_type": self.node_type.value,
            "emotion_tags": self.emotion_tags,
            "children": self.children,
            "is_terminal": self.is_terminal,
        }


@dataclass
class DialogueTree:
    """A complete dialogue tree with branching nodes."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    npc_id: str = ""
    npc_name: str = ""
    npc_personality: str = ""
    nodes: Dict[str, DialogueLine] = field(default_factory=dict)
    root_id: str = ""
    current_node_id: str = ""
    mood: ConversationMood = ConversationMood.NEUTRAL
    context_tags: List[str] = field(default_factory=list)
    repeat_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "npc_id": self.npc_id,
            "npc_name": self.npc_name,
            "npc_personality": self.npc_personality,
            "node_count": len(self.nodes),
            "current_node_id": self.current_node_id,
            "mood": self.mood.value,
            "context_tags": self.context_tags,
            "repeat_count": self.repeat_count,
        }


@dataclass
class ConversationSession:
    """An active conversation session between player and NPC."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tree_id: str = ""
    npc_id: str = ""
    player_id: str = ""
    dialogue_history: List[Dict[str, Any]] = field(default_factory=list)
    current_node_id: str = ""
    started_at: float = field(default_factory=_time_module.time)
    last_activity: float = field(default_factory=_time_module.time)
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tree_id": self.tree_id,
            "npc_id": self.npc_id,
            "player_id": self.player_id,
            "line_count": len(self.dialogue_history),
            "current_node_id": self.current_node_id,
            "is_active": self.is_active,
            "started_at": self.started_at,
        }


class AgentDialogueEngine:
    """
    Context-aware dialogue generation system.
    Singleton pattern with thread-safe initialization.
    """

    _instance: Optional["AgentDialogueEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentDialogueEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentDialogueEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._trees: Dict[str, DialogueTree] = {}
        self._sessions: Dict[str, ConversationSession] = {}
        self._total_trees: int = 0
        self._total_sessions: int = 0

    def create_dialogue_tree(
        self,
        title: str,
        npc_id: str,
        npc_name: str,
        npc_personality: str = "neutral",
        context_tags: Optional[List[str]] = None,
    ) -> DialogueTree:
        with self._lock:
            tree = DialogueTree(
                title=title,
                npc_id=npc_id,
                npc_name=npc_name,
                npc_personality=npc_personality,
                context_tags=context_tags or [],
            )
            self._trees[tree.id] = tree
            self._total_trees += 1
            return tree

    def add_npc_line(
        self,
        tree_id: str,
        text: str,
        tone: DialogueTone = DialogueTone.NEUTRAL,
        parent_id: str = "",
        node_type: DialogueNodeType = DialogueNodeType.NPC_LINE,
        is_terminal: bool = False,
        emotion_tags: Optional[List[str]] = None,
    ) -> Optional[DialogueLine]:
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            line = DialogueLine(
                speaker_id=tree.npc_id,
                speaker_name=tree.npc_name,
                text=text,
                tone=tone,
                node_type=node_type,
                emotion_tags=emotion_tags or [],
                parent_id=parent_id,
                is_terminal=is_terminal,
                order_index=len(tree.nodes),
            )
            tree.nodes[line.id] = line

            if parent_id and parent_id in tree.nodes:
                tree.nodes[parent_id].children.append(line.id)

            if not tree.root_id:
                tree.root_id = line.id
                tree.current_node_id = line.id

            return line

    def add_player_choice(
        self,
        tree_id: str,
        text: str,
        parent_id: str = "",
        leads_to_node_id: str = "",
    ) -> Optional[DialogueLine]:
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            choice = DialogueLine(
                speaker_id="player",
                speaker_name="Player",
                text=text,
                tone=DialogueTone.NEUTRAL,
                node_type=DialogueNodeType.PLAYER_CHOICE,
                parent_id=parent_id,
                order_index=len(tree.nodes),
            )
            tree.nodes[choice.id] = choice

            if parent_id and parent_id in tree.nodes:
                tree.nodes[parent_id].children.append(choice.id)

            if leads_to_node_id and leads_to_node_id in tree.nodes:
                choice.children.append(leads_to_node_id)

            return choice

    def start_session(
        self, tree_id: str, player_id: str = "player"
    ) -> Optional[ConversationSession]:
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            session = ConversationSession(
                tree_id=tree_id,
                npc_id=tree.npc_id,
                player_id=player_id,
                current_node_id=tree.root_id,
            )
            self._sessions[session.id] = session
            self._total_sessions += 1
            tree.repeat_count += 1
            return session

    def get_current_line(self, session_id: str) -> Optional[DialogueLine]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        tree = self._trees.get(session.tree_id)
        if tree is None:
            return None
        return tree.nodes.get(session.current_node_id)

    def get_available_choices(self, session_id: str) -> List[DialogueLine]:
        session = self._sessions.get(session_id)
        if session is None:
            return []
        tree = self._trees.get(session.tree_id)
        if tree is None:
            return []
        current = tree.nodes.get(session.current_node_id)
        if current is None:
            return []
        return [tree.nodes[cid] for cid in current.children if cid in tree.nodes]

    def select_choice(
        self, session_id: str, choice_id: str
    ) -> Optional[DialogueLine]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            tree = self._trees.get(session.tree_id)
            if tree is None:
                return None

            choice = tree.nodes.get(choice_id)
            if choice is None:
                return None

            session.dialogue_history.append({
                "node_id": choice_id,
                "text": choice.text,
                "speaker": choice.speaker_name,
                "timestamp": _time_module.time(),
            })
            session.last_activity = _time_module.time()

            if choice.children:
                next_node_id = choice.children[0]
                session.current_node_id = next_node_id
                next_line = tree.nodes.get(next_node_id)
                if next_line:
                    session.dialogue_history.append({
                        "node_id": next_node_id,
                        "text": next_line.text,
                        "speaker": next_line.speaker_name,
                        "timestamp": _time_module.time(),
                    })
                return next_line

            return None

    def advance_dialogue(self, session_id: str) -> Optional[DialogueLine]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        tree = self._trees.get(session.tree_id)
        if tree is None:
            return None

        current = tree.nodes.get(session.current_node_id)
        if current is None:
            return None

        if current.is_terminal:
            return None

        if current.children:
            next_node_id = current.children[0]
            session.current_node_id = next_node_id
            next_line = tree.nodes.get(next_node_id)
            if next_line:
                session.dialogue_history.append({
                    "node_id": next_node_id,
                    "text": next_line.text,
                    "speaker": next_line.speaker_name,
                    "timestamp": _time_module.time(),
                })
            session.last_activity = _time_module.time()
            return next_line

        return None

    def end_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.is_active = False
            return True

    def get_tree(self, tree_id: str) -> Optional[DialogueTree]:
        return self._trees.get(tree_id)

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(session_id)

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session is None:
            return []
        return session.dialogue_history

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active_sessions = sum(1 for s in self._sessions.values() if s.is_active)
            return {
                "total_trees": self._total_trees,
                "total_sessions": self._total_sessions,
                "active_sessions": active_sessions,
                "total_nodes": sum(len(t.nodes) for t in self._trees.values()),
                "total_lines": sum(len(s.dialogue_history) for s in self._sessions.values()),
            }

    def get_all_trees(self, limit: int = 10) -> List[Dict[str, Any]]:
        trees = list(self._trees.values())[:limit]
        return [t.to_dict() for t in trees]

    def get_all_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        sessions = list(self._sessions.values())[:limit]
        return [s.to_dict() for s in sessions]


def get_dialogue_engine() -> AgentDialogueEngine:
    return AgentDialogueEngine.get_instance()