"""
Agent Dialogue System - AI-driven dialogue generation for the game engine.
Provides branching conversations, NPC personality modeling, dialogue trees,
and context-aware response generation for believable character interactions.
"""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DialogueStyle(Enum):
    """Personality-driven dialogue styles for NPC speech patterns."""
    FORMAL = "formal"
    CASUAL = "casual"
    MYSTERIOUS = "mysterious"
    AGGRESSIVE = "aggressive"
    FRIENDLY = "friendly"
    SARCASTIC = "sarcastic"
    FEARFUL = "fearful"
    WISE = "wise"
    HUMOROUS = "humorous"
    MELANCHOLIC = "melancholic"


class EmotionTone(Enum):
    """Emotional tones that color NPC dialogue delivery."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    AFRAID = "afraid"
    DISGUSTED = "disgusted"
    EXCITED = "excited"


class RelationshipLevel(Enum):
    """Progression of relationship intimacy between player and NPC."""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    ALLY = "ally"
    RIVAL = "rival"
    ENEMY = "enemy"


@dataclass
class NPCPersonality:
    """Full personality profile for an NPC character including traits and knowledge."""
    npc_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: str = ""
    style: DialogueStyle = DialogueStyle.CASUAL
    default_tone: EmotionTone = EmotionTone.NEUTRAL
    traits: List[str] = field(default_factory=list)
    background: str = ""
    knowledge_topics: List[str] = field(default_factory=list)
    speech_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "role": self.role,
            "style": self.style.value,
            "default_tone": self.default_tone.value,
            "traits": self.traits,
            "background": self.background,
            "knowledge_topics": self.knowledge_topics,
            "speech_patterns": self.speech_patterns,
        }


@dataclass
class DialogueNode:
    """A single node within a dialogue tree representing one NPC utterance."""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    npc_id: str = ""
    text: str = ""
    tone: EmotionTone = EmotionTone.NEUTRAL
    conditions: Dict[str, Any] = field(default_factory=dict)
    responses: List[Dict[str, Any]] = field(default_factory=list)
    leads_to: List[str] = field(default_factory=list)
    is_ending: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "npc_id": self.npc_id,
            "text": self.text,
            "tone": self.tone.value,
            "conditions": self.conditions,
            "responses": self.responses,
            "leads_to": self.leads_to,
            "is_ending": self.is_ending,
            "metadata": self.metadata,
        }


@dataclass
class DialogueTree:
    """A complete dialogue tree with all nodes and branching structure."""
    tree_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    npc_id: str = ""
    title: str = ""
    root_node: str = ""
    nodes: Dict[str, DialogueNode] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "npc_id": self.npc_id,
            "title": self.title,
            "root_node": self.root_node,
            "node_count": len(self.nodes),
            "context": self.context,
            "created_at": self.created_at,
        }


@dataclass
class ConversationSession:
    """Active conversation session tracking state between player and NPC."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    npc_id: str = ""
    dialogue_tree_id: str = ""
    current_node: str = ""
    history: deque = field(default_factory=lambda: deque(maxlen=200))
    state: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "npc_id": self.npc_id,
            "dialogue_tree_id": self.dialogue_tree_id,
            "current_node": self.current_node,
            "history": list(self.history),
            "state": self.state,
            "started_at": self.started_at,
        }


# ---------------------------------------------------------------------------
# Dialogue Template Banks
# ---------------------------------------------------------------------------

_STYLE_GREETINGS: Dict[str, List[str]] = {
    "formal": [
        "Greetings, {player_name}. It is an honor to make your acquaintance.",
        "Well met, {player_name}. I trust the day finds you in good health.",
        "Good day to you, {player_name}. How may I be of service?",
        "Salutations, {player_name}. I have been expecting you.",
    ],
    "casual": [
        "Hey there, {player_name}! What's up?",
        "Oh, {player_name}! Didn't see you there. How's it going?",
        "Yo, {player_name}! Good to see you around.",
        "Hey {player_name}! Been a minute. What brings you here?",
    ],
    "mysterious": [
        "Ah... {player_name}. I wondered when you would arrive.",
        "The shadows whisper your name, {player_name}. We meet at last.",
        "So. You have found me, {player_name}. Few manage that.",
        "{player_name}... yes, I have been watching your journey.",
    ],
    "aggressive": [
        "What do you want, {player_name}? Make it quick.",
        "You again, {player_name}. I don't have time for this.",
        "State your business, {player_name}. Now.",
        "{player_name}. This had better be important.",
    ],
    "friendly": [
        "{player_name}! So wonderful to see you!",
        "Well hello there, {player_name}! You look great today!",
        "{player_name}, my friend! Come in, come in!",
        "Oh {player_name}! I was just thinking about you!",
    ],
    "sarcastic": [
        "Oh look, it's {player_name}. What a delightful surprise.",
        "Well well well. If it isn't {player_name}. To what do I owe this honor?",
        "Ah, {player_name}. I was just saying how quiet it was. Too quiet.",
        "Perfect timing, {player_name}. I was almost bored.",
    ],
    "fearful": [
        "Oh! {player_name}... I-I didn't hear you coming.",
        "{player_name}? Please don't startle me like that.",
        "Is it really you, {player_name}? I was so worried...",
        "{player_name}... thank goodness. I thought something terrible happened.",
    ],
    "wise": [
        "Ah, {player_name}. The path has led you here, as I foresaw.",
        "Welcome, {player_name}. There is much to discuss.",
        "{player_name}. Your arrival was written in the stars.",
        "Come, {player_name}. Sit with me. Questions burn in your heart.",
    ],
    "humorous": [
        "{player_name}! You won't believe what just happened!",
        "Haha, {player_name}! Perfect timing for the joke I just heard!",
        "Well if it isn't my favorite adventurer! What'd you break this time?",
        "{player_name}! Quick, help me hide this before the guards see!",
    ],
    "melancholic": [
        "{player_name}... even you've come back. That's... something, I suppose.",
        "Oh. It's you, {player_name}. I didn't expect anyone today.",
        "{player_name}... the days all blur together anymore.",
        "Hello, {player_name}. I was just reminiscing about better times.",
    ],
}

_STYLE_FAREWELLS: Dict[str, List[str]] = {
    "formal": [
        "Farewell, {player_name}. May fortune smile upon your endeavors.",
        "Until we meet again, {player_name}. Travel safely.",
        "I bid you good day, {player_name}. Do return when convenient.",
        "May the road rise to meet you, {player_name}.",
    ],
    "casual": [
        "Catch you later, {player_name}! Take care!",
        "See ya, {player_name}! Don't be a stranger!",
        "Later {player_name}! Good luck out there!",
        "Alright, {player_name}, I'll see you around!",
    ],
    "mysterious": [
        "Go now, {player_name}. The threads of fate pull you onward.",
        "We shall meet again, {player_name}, when the time is right.",
        "Remember what I've told you, {player_name}. It will matter soon.",
        "The veil parts for you, {player_name}. Walk carefully.",
    ],
    "aggressive": [
        "Get out of my sight, {player_name}.",
        "We're done here. Leave.",
        "Don't come back unless you have what I asked for.",
        "Fine. Go. But this isn't over.",
    ],
    "friendly": [
        "Bye {player_name}! Come back anytime!",
        "Take care of yourself, {player_name}! I'll miss you!",
        "See you soon, {player_name}! Don't forget to visit!",
        "Hugs, {player_name}! Safe travels!",
    ],
    "sarcastic": [
        "Try not to trip on your way out, {player_name}.",
        "Oh, leaving so soon? And here I was just getting comfortable.",
        "Don't let the door hit you. Seriously, the hinges are old.",
        "Well, this has been... an experience. Until next time, {player_name}.",
    ],
    "fearful": [
        "Stay safe out there, {player_name}. Please be careful.",
        "Come back soon, {player_name}. I'll worry otherwise.",
        "Just... just be careful, {player_name}. There are dangers everywhere.",
        "Go quickly, {player_name}. Before anyone sees you.",
    ],
    "wise": [
        "Go forth, {player_name}. Your destiny awaits you.",
        "Remember the lessons you have learned here today.",
        "The road ahead is long, {player_name}. But you are ready.",
        "May wisdom guide your steps, {player_name}.",
    ],
    "humorous": [
        "Don't do anything I wouldn't do! Which leaves you a lot of options.",
        "Bye {player_name}! Try not to blow anything up!",
        "If you see my ex, you didn't see me. Got it?",
        "Until next time, {player_name}! Bring snacks!",
    ],
    "melancholic": [
        "Goodbye, {player_name}. It was nice having company, for a while.",
        "Take care, {player_name}. Not everyone does anymore.",
        "I'll be here if you need me. Same place as always.",
        "Go on, {player_name}. Don't let me hold you back.",
    ],
}

_RELATIONSHIP_MODIFIERS: Dict[str, str] = {
    "stranger": "with measured distance",
    "acquaintance": "with polite familiarity",
    "friend": "with warm recognition",
    "close_friend": "with deep trust and openness",
    "ally": "with shared purpose and loyalty",
    "rival": "with competitive tension",
    "enemy": "with barely concealed hostility",
}

_TONE_ADJECTIVES: Dict[str, List[str]] = {
    "neutral": ["steadily", "plainly", "matter-of-factly", "evenly"],
    "happy": ["cheerfully", "brightly", "joyfully", "warmly"],
    "sad": ["sorrowfully", "mournfully", "gloomily", "with a heavy sigh"],
    "angry": ["sharply", "harshly", "with clenched fists", "through gritted teeth"],
    "surprised": ["with wide eyes", "incredulously", "with a start", "taken aback"],
    "afraid": ["nervously", "with a trembling voice", "in a hushed whisper", "anxiously"],
    "disgusted": ["with a sneer", "wrinkling the nose", "with visible distaste", "curling the lip"],
    "excited": ["eagerly", "with barely contained enthusiasm", "bubbling over", "eyes gleaming"],
}

_TONE_PREFIXES: Dict[str, List[str]] = {
    "neutral": ["", ""],
    "happy": ["(smiling) ", "(grinning) "],
    "sad": ["(sighing) ", "(looking down) "],
    "angry": ["(scowling) ", "(fuming) "],
    "surprised": ["(blinking) ", "(eyes widening) "],
    "afraid": ["(glancing around) ", "(lowering voice) "],
    "disgusted": ["(wincing) ", "(stepping back) "],
    "excited": ["(beaming) ", "(leaning forward) "],
}

_TOPIC_TEMPLATES: Dict[str, List[str]] = {
    "combat": [
        "A true warrior knows {lesson}.",
        "The key to survival is {wisdom}.",
        "I've faced {enemy_type} more times than I can count.",
        "{strategy} is the difference between victory and defeat.",
    ],
    "magic": [
        "The arcane arts require {attribute}, above all else.",
        "Spells are not just words; they are {insight}.",
        "I studied {school} magic for {years} before I understood it.",
        "Magic flows through {source}, much like {metaphor}.",
    ],
    "history": [
        "In the {era}, these lands were ruled by {ruler}.",
        "They say {event} changed the course of our kingdom forever.",
        "Few remember the truth about {figure}. The records were... altered.",
        "Before the {conflict}, this region was known as {old_name}.",
    ],
    "trade": [
        "Supply and demand rule everything, even here in {location}.",
        "If you need {item_type}, I know someone who can get it.",
        "That's a fair price, {player_name}. But I could offer {alternative}.",
        "{commodity} prices have been volatile since {recent_event}.",
    ],
    "secrets": [
        "Not many know about {secret_place}. And I'd like to keep it that way.",
        "There are things about {person} that would shock you.",
        "The {organization} has been operating here for {duration}.",
        "I shouldn't tell you this, but {dangerous_info}.",
    ],
    "nature": [
        "The {herb} grows only during the {season} moon.",
        "You can navigate these woods by watching the {sign}.",
        "That creature... it's a {species}. More dangerous than it looks.",
        "The river changes course every {cycle}. Few outsiders know that.",
    ],
    "culture": [
        "In our tradition, the {ceremony} marks a coming of age.",
        "The festival of {festival_name} dates back to {origin}.",
        "Our people believe that {belief}. It guides everything we do.",
        "The song you heard... it's an old {cultural_form} about {theme}.",
    ],
    "danger": [
        "Stay away from {dangerous_place} at night. That's not superstition.",
        "I've seen what {threat} can do. You don't want to face it unprepared.",
        "If you value your life, {survival_tip}.",
        "The last person who tried that... well, let's just say {consequence}.",
    ],
}

_SPEECH_PATTERN_TRANSFORMS: Dict[str, Dict[str, Any]] = {
    "verbose": {
        "prefix": "I must say, upon careful reflection and consideration of all the relevant factors, ",
        "suffix": ", if you truly want to understand the full scope of what I'm trying to convey.",
        "expand": True,
    },
    "terse": {
        "prefix": "",
        "suffix": "",
        "expand": False,
        "truncate": True,
    },
    "metaphorical": {
        "metaphors": [
            "It's like {tenor} dancing with {vehicle}.",
            "Think of it as {tenor} wrapped in {vehicle}.",
            "A {tenor} among {vehicle}, so to speak.",
            "Imagine {tenor} riding on the back of {vehicle}.",
        ],
    },
    "repetitive": {
        "echo_word": True,
        "suffix_template": " I tell you. I really do tell you.",
    },
    "uses slang": {
        "slang_terms": ["ain't", "gonna", "wanna", "ya know", "kinda", "sorta", "like"],
    },
    "poetic": {
        "alliteration": True,
        "rhyme_words": True,
    },
    "nervous": {
        "fillers": ["um", "uh", "er", "well, um", "uhh"],
        "stutter": True,
    },
    "loud": {
        "capitalize": True,
        "exclamations": True,
    },
    "quiet": {
        "lowercase": True,
        "soften": True,
        "softeners": ["perhaps", "maybe", "if you don't mind", "I think"],
    },
}

_METAPHOR_TENORS: List[str] = [
    "hope", "fear", "courage", "doubt", "love", "hate", "wisdom",
    "folly", "truth", "deception", "strength", "weakness", "honor", "betrayal",
]

_METAPHOR_VEHICLES: List[str] = [
    "a raging storm", "a gentle breeze", "a blazing fire", "deep water",
    "a towering mountain", "a fragile flower", "a sharp blade",
    "a tangled web", "a rising sun", "a falling star", "a winding path",
    "a roaring lion", "a silent shadow", "a broken mirror",
]


# ---------------------------------------------------------------------------
# DialogueSystemEngine
# ---------------------------------------------------------------------------


class DialogueSystemEngine:
    """
    AI-driven dialogue system that generates branching conversations, manages
    NPC personalities, builds dialogue trees, and produces context-aware responses.
    """

    _instance: Optional["DialogueSystemEngine"] = None
    _lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "DialogueSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._npcs: Dict[str, NPCPersonality] = {}
        self._dialogue_trees: Dict[str, DialogueTree] = {}
        self._conversations: Dict[str, ConversationSession] = {}
        self._node_index: Dict[str, str] = {}
        self._total_npcs_created: int = 0
        self._total_trees_created: int = 0
        self._total_conversations_started: int = 0
        self._total_dialogues_generated: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "DialogueSystemEngine":
        return cls()

    # ------------------------------------------------------------------
    # NPC Management
    # ------------------------------------------------------------------

    def create_npc(
        self,
        name: str,
        role: str = "",
        style: str = "casual",
        traits: Optional[List[str]] = None,
        background: str = "",
        knowledge_topics: Optional[List[str]] = None,
        speech_patterns: Optional[List[str]] = None,
    ) -> NPCPersonality:
        """Create and register a new NPC personality profile."""
        try:
            ds = DialogueStyle(style.lower())
        except ValueError:
            ds = DialogueStyle.CASUAL

        npc = NPCPersonality(
            name=name,
            role=role,
            style=ds,
            traits=traits or [],
            background=background,
            knowledge_topics=knowledge_topics or [],
            speech_patterns=speech_patterns or [],
        )

        with self._lock:
            self._npcs[npc.npc_id] = npc
            self._total_npcs_created += 1

        return npc

    def get_npc(self, npc_id: str) -> Optional[NPCPersonality]:
        """Retrieve an NPC by its identifier."""
        return self._npcs.get(npc_id)

    def list_npcs(self) -> List[NPCPersonality]:
        """Return all registered NPC personality profiles."""
        return list(self._npcs.values())

    # ------------------------------------------------------------------
    # Dialogue Tree Construction
    # ------------------------------------------------------------------

    def create_dialogue_tree(
        self,
        npc_id: str,
        title: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[DialogueTree]:
        """Create a new dialogue tree for a specific NPC."""
        npc = self._npcs.get(npc_id)
        if npc is None:
            return None

        tree = DialogueTree(
            npc_id=npc_id,
            title=title,
            context=context or {},
        )

        with self._lock:
            self._dialogue_trees[tree.tree_id] = tree
            self._total_trees_created += 1

        return tree

    def add_dialogue_node(
        self,
        tree_id: str,
        text: str,
        tone: str = "neutral",
        conditions: Optional[Dict[str, Any]] = None,
        parent_node_id: Optional[str] = None,
    ) -> Optional[DialogueNode]:
        """Add a dialogue node to a tree, optionally linking to a parent."""
        tree = self._dialogue_trees.get(tree_id)
        if tree is None:
            return None

        try:
            et = EmotionTone(tone.lower())
        except ValueError:
            et = EmotionTone.NEUTRAL

        node = DialogueNode(
            npc_id=tree.npc_id,
            text=text,
            tone=et,
            conditions=conditions or {},
        )

        with self._lock:
            tree.nodes[node.node_id] = node
            self._node_index[node.node_id] = tree_id

            if parent_node_id and parent_node_id in tree.nodes:
                parent = tree.nodes[parent_node_id]
                parent.leads_to.append(node.node_id)
            else:
                tree.root_node = node.node_id

        return node

    def add_response_option(
        self,
        node_id: str,
        text: str,
        leads_to_node_id: str = "",
        conditions: Optional[Dict[str, Any]] = None,
    ) -> Optional[DialogueNode]:
        """Add a player response option to a dialogue node."""
        tree_id = self._node_index.get(node_id)
        if tree_id is None:
            return None

        tree = self._dialogue_trees.get(tree_id)
        if tree is None or node_id not in tree.nodes:
            return None

        node = tree.nodes[node_id]
        option = {
            "text": text,
            "leads_to_node_id": leads_to_node_id,
            "conditions": conditions or {},
        }
        node.responses.append(option)

        if leads_to_node_id:
            node.leads_to.append(leads_to_node_id)

        return node

    # ------------------------------------------------------------------
    # Conversation Session Management
    # ------------------------------------------------------------------

    def start_conversation(
        self,
        player_id: str,
        npc_id: str,
        tree_id: str,
    ) -> Optional[ConversationSession]:
        """Begin a new conversation session between a player and NPC."""
        tree = self._dialogue_trees.get(tree_id)
        if tree is None:
            return None
        if tree.npc_id != npc_id:
            return None

        session = ConversationSession(
            player_id=player_id,
            npc_id=npc_id,
            dialogue_tree_id=tree_id,
            current_node=tree.root_node,
        )

        with self._lock:
            self._conversations[session.session_id] = session
            self._total_conversations_started += 1

        root_node = tree.nodes.get(tree.root_node)
        if root_node:
            session.history.append({
                "node_id": root_node.node_id,
                "text": root_node.text,
                "speaker": "npc",
                "timestamp": time.time(),
            })

        return session

    def select_response(
        self,
        session_id: str,
        response_index: int,
    ) -> Optional[DialogueNode]:
        """Process a player response and advance to the next dialogue node."""
        session = self._conversations.get(session_id)
        if session is None:
            return None

        tree = self._dialogue_trees.get(session.dialogue_tree_id)
        if tree is None:
            return None

        current = tree.nodes.get(session.current_node)
        if current is None:
            return None
        if response_index < 0 or response_index >= len(current.responses):
            return None

        chosen = current.responses[response_index]
        chosen_text = chosen.get("text", "")
        leads_to_id = chosen.get("leads_to_node_id", "")

        session.history.append({
            "node_id": session.current_node,
            "text": chosen_text,
            "speaker": "player",
            "timestamp": time.time(),
            "response_index": response_index,
        })

        if not leads_to_id or leads_to_id not in tree.nodes:
            end_node = DialogueNode(
                npc_id=session.npc_id,
                text="...",
                tone=EmotionTone.NEUTRAL,
                is_ending=True,
            )
            self._node_index[end_node.node_id] = session.dialogue_tree_id
            return end_node

        next_node = tree.nodes[leads_to_id]
        session.current_node = next_node.node_id

        session.history.append({
            "node_id": next_node.node_id,
            "text": next_node.text,
            "speaker": "npc",
            "timestamp": time.time(),
        })

        return next_node

    # ------------------------------------------------------------------
    # Dialogue Generation
    # ------------------------------------------------------------------

    def generate_greeting(
        self,
        npc_id: str,
        player_relationship: str = "stranger",
    ) -> str:
        """Generate a context-appropriate greeting from an NPC."""
        npc = self._npcs.get(npc_id)
        if npc is None:
            return "Hello."

        style_key = npc.style.value
        templates = _STYLE_GREETINGS.get(style_key, _STYLE_GREETINGS["casual"])
        base = random.choice(templates)
        greeting = base.format(player_name="friend")

        rel_modifier = _RELATIONSHIP_MODIFIERS.get(
            player_relationship, "with polite distance"
        )
        greeting = self._apply_speech_patterns(greeting, npc, f"Said {rel_modifier}.")

        self._total_dialogues_generated += 1
        return greeting

    def generate_farewell(
        self,
        npc_id: str,
        mood: str = "neutral",
    ) -> str:
        """Generate a context-appropriate farewell from an NPC."""
        npc = self._npcs.get(npc_id)
        if npc is None:
            return "Goodbye."

        style_key = npc.style.value
        templates = _STYLE_FAREWELLS.get(style_key, _STYLE_FAREWELLS["casual"])
        base = random.choice(templates)
        farewell = base.format(player_name="friend")

        try:
            tone = EmotionTone(mood.lower())
        except ValueError:
            tone = npc.default_tone

        farewell = self._apply_tone(farewell, tone)
        farewell = self._apply_speech_patterns(farewell, npc, "")

        self._total_dialogues_generated += 1
        return farewell

    def generate_dialogue(
        self,
        npc_id: str,
        context: Dict[str, Any],
        tone: str = "neutral",
    ) -> str:
        """
        Generate context-aware dialogue based on NPC personality, relationship,
        emotional tone, knowledge topics, and speech patterns.
        """
        npc = self._npcs.get(npc_id)
        if npc is None:
            return "I have nothing to say."

        try:
            et = EmotionTone(tone.lower())
        except ValueError:
            et = npc.default_tone

        relationship = context.get("relationship", "stranger")
        topic = context.get("topic", "")
        player_name = context.get("player_name", "friend")
        situation = context.get("situation", "")
        extra_context = context.get("extra_context", {})

        dialogue = self._build_dialogue_from_context(
            npc=npc,
            tone=et,
            relationship=relationship,
            topic=topic,
            player_name=player_name,
            situation=situation,
            extra_context=extra_context,
        )

        dialogue = self._apply_speech_patterns(dialogue, npc, "")

        self._total_dialogues_generated += 1
        return dialogue

    def _build_dialogue_from_context(
        self,
        npc: NPCPersonality,
        tone: EmotionTone,
        relationship: str,
        topic: str,
        player_name: str,
        situation: str,
        extra_context: Dict[str, Any],
    ) -> str:
        """Assemble dialogue from template banks based on full context."""

        # Select topic template if the NPC has knowledge in that area
        topic_text: Optional[str] = None
        if topic and topic in _TOPIC_TEMPLATES:
            if topic in npc.knowledge_topics or not npc.knowledge_topics:
                template = random.choice(_TOPIC_TEMPLATES[topic])
                topic_text = template.format(
                    lesson=random.choice(["patience", "timing", "instinct", "discipline"]),
                    wisdom=random.choice(["knowing when to strike", "understanding your enemy", "controlling fear", "staying alert"]),
                    enemy_type=random.choice(["bandits", "shadow beasts", "rogue mages", "undead"]),
                    strategy=random.choice(["Positioning", "Resource management", "Patience", "Adaptability"]),
                    attribute=random.choice(["focus", "discipline", "intuition", "sacrifice"]),
                    insight=random.choice(["intent given form", "the language of the soul", "nature bent to will", "an echo of creation"]),
                    school=random.choice(["elemental", "illusion", "restoration", "necromantic"]),
                    years=random.choice(["decades", "a lifetime", "since I was a child", "longer than you'd believe"]),
                    source=random.choice(["ley lines", "the heart", "ancient runes", "the void itself"]),
                    metaphor=random.choice(["a river carving stone", "fire seeking air", "roots binding earth", "stars guiding sailors"]),
                    era=random.choice(["Age of Iron", "Dawn Era", "Twilight Century", "Reclamation Period"]),
                    ruler=random.choice(["the Mad King", "the Seven Houses", "the Council of Mages", "warring chieftains"]),
                    event=random.choice(["the Sundering", "the Great Collapse", "the Pact of Ash", "the Last Convergence"]),
                    figure=random.choice(["Emperor Aldric", "Lady Vex", "the First Watcher", "the Nameless Scholar"]),
                    conflict=random.choice(["Border Wars", "Plague Years", "Mage Rebellion", "Serpent Schism"]),
                    old_name=random.choice(["Veridia", "Northvale", "Sunken Reach", "Aelindor"]),
                    location=random.choice(["this town", "the capital", "the borderlands", "these mountains"]),
                    item_type=random.choice(["enchanted blades", "rare herbs", "ancient tomes", "quality armor"]),
                    alternative=random.choice(["a trade instead", "a favor in return", "information as payment", "a discount for regulars"]),
                    commodity=random.choice(["Iron ore", "Spice", "Silk", "Crystals"]),
                    recent_event=random.choice(["the blockade", "the harvest failure", "the dragon sightings", "the guild merger"]),
                    secret_place=random.choice(["the crypt beneath the chapel", "the old watchtower", "the cave behind the waterfall", "the cellar of the inn"]),
                    person=random.choice(["the mayor", "Captain Voss", "Lady Marche", "the blind seer"]),
                    organization=random.choice(["Shadow Guild", "Circle of Nine", "Free Merchants", "Iron Covenant"]),
                    duration=random.choice(["years", "decades", "generations", "centuries"]),
                    dangerous_info=random.choice(["there's a traitor in the council", "the mine was never empty", "the healer knows more than she tells", "someone's been smuggling through the east gate"]),
                    herb=random.choice(["moonshade", "sunpetal", "frostbloom", "emberroot"]),
                    season=random.choice(["third", "harvest", "deep winter", "first thaw"]),
                    sign=random.choice(["moss patterns", "bird calls", "star alignment", "wind direction"]),
                    species=random.choice(["crag wolf", "marsh wyrm", "blackfeather harpy", "ash strider"]),
                    cycle=random.choice(["few years", "decade", "generation", "century"]),
                    ceremony=random.choice(["Rite of Embers", "Naming Ceremony", "First Hunt", "Silent Vigil"]),
                    festival_name=random.choice(["Luminara", "Harvestmoot", "The Bitter Feast", "Starcross"]),
                    origin=random.choice(["the founding of the city", "the first migration", "the fall of the old kingdom", "a treaty with the fey"]),
                    belief=random.choice(["the dead walk among us", "every stone has a soul", "water remembers all things", "fire cleanses truth from lies"]),
                    cultural_form=random.choice(["ballad", "chant", "lament", "work song"]),
                    theme=random.choice(["lost love", "heroic sacrifice", "trickster's triumph", "the endless sea"]),
                    dangerous_place=random.choice(["the Hollow Road", "Widow's Crossing", "the Sunken Quarter", "Barrow Downs"]),
                    threat=random.choice(["a cave troll", "corruption magic", "the voidlings", "a wendigo"]),
                    survival_tip=random.choice(["always carry salt", "never whistle at dusk", "trust the crows", "keep iron on you"]),
                    consequence=random.choice(["they were never seen again", "their screams echoed for hours", "only bones were found", "the tale still scares children"]),
                    player_name=player_name,
                    **(extra_context or {}),
                )

        # Build dialogue based on available components
        parts: List[str] = []

        # Opening based on relationship and tone
        opening = self._build_opening(npc, tone, relationship, player_name, situation)
        if opening:
            parts.append(opening)

        # Body based on knowledge/topic
        if topic_text:
            parts.append(topic_text)
        elif npc.traits:
            trait_response = self._build_trait_response(npc, tone, player_name)
            if trait_response:
                parts.append(trait_response)
        else:
            generic = self._build_generic_response(npc, tone, player_name)
            parts.append(generic)

        dialogue = " ".join(parts)
        dialogue = self._apply_tone(dialogue, tone)
        return dialogue

    def _build_opening(
        self,
        npc: NPCPersonality,
        tone: EmotionTone,
        relationship: str,
        player_name: str,
        situation: str,
    ) -> str:
        """Build the opening phrase of a generated dialogue."""
        rel_modifier = _RELATIONSHIP_MODIFIERS.get(relationship, "")

        openings: List[str] = []
        if situation:
            openings.append(f"Regarding {situation},")
        elif relationship == "stranger":
            openings.append("I'm not sure I should be speaking of this, but")
        elif relationship == "enemy":
            openings.append("I shouldn't be telling you this, but")
        elif relationship == "close_friend" or relationship == "ally":
            openings.append(f"Between you and me, {player_name},")
        elif relationship == "friend":
            openings.append(f"Since you asked, {player_name},")
        else:
            openings.append("Let me put it this way.")

        if openings:
            opening = random.choice(openings)
        else:
            opening = "Listen."

        return opening

    def _build_trait_response(
        self,
        npc: NPCPersonality,
        tone: EmotionTone,
        player_name: str,
    ) -> str:
        """Build dialogue that reflects NPC personality traits."""
        trait = random.choice(npc.traits)

        trait_library: Dict[str, List[str]] = {
            "brave": [
                "I've faced worse and walked away.",
                "Fear is just a reminder that you're still alive.",
                "Someone has to stand up. Might as well be me.",
            ],
            "cowardly": [
                "I'd rather not get involved, if it's all the same.",
                "There's no shame in running. Shame is for the dead.",
                "You go first. I'll... keep watch here.",
            ],
            "honest": [
                "I'll tell you plainly: this isn't a good idea.",
                "Truth is, I've never seen anything like it.",
                "I won't lie to you. Things are bad.",
            ],
            "deceitful": [
                "Trust me. When have I ever led you wrong?",
                "The situation is... manageable. Completely manageable.",
                "I'm sure everything is exactly as it appears.",
            ],
            "curious": [
                "I've been studying this for weeks. Fascinating stuff.",
                "Did you notice that? The pattern, I mean.",
                "There's more here than meets the eye, I'm certain of it.",
            ],
            "apathetic": [
                "Does it really matter? In the grand scheme of things?",
                "Things happen. Things stop happening. That's life.",
                "Why ask me? I'm just as lost as everyone else.",
            ],
            "optimistic": [
                "I have a good feeling about this!",
                "Every problem has a solution. We just haven't found it yet.",
                "Things always work out in the end, {player_name}.",
            ],
            "pessimistic": [
                "What's the point? We've tried everything.",
                "I knew this would happen. I just knew it.",
                "Don't get your hopes up, {player_name}. That way lies disappointment.",
            ],
            "loyal": [
                "You've stood by me. I'll stand by you.",
                "I don't abandon my friends. Ever.",
                "Whatever you decide, I'm with you.",
            ],
            "impulsive": [
                "Let's just do it! What's the worst that could happen?",
                "I already went ahead and... well, you'll see.",
                "Planning is overrated. Action is what counts!",
            ],
            "cautious": [
                "Let's think this through before we do anything rash.",
                "I've mapped out three possible approaches.",
                "One wrong step and this all falls apart.",
            ],
            "generous": [
                "Take what you need. I have plenty.",
                "Helping others isn't a burden; it's what makes life worth living.",
                "Don't worry about paying me back. Just pay it forward.",
            ],
            "greedy": [
                "What's in it for me?",
                "Information isn't free, {player_name}. You know that.",
                "I could help you... for a price.",
            ],
        }

        base_texts = trait_library.get(
            trait.lower(),
            ["That's just how I see things."],
        )
        return random.choice(base_texts).format(player_name=player_name)

    def _build_generic_response(
        self,
        npc: NPCPersonality,
        tone: EmotionTone,
        player_name: str,
    ) -> str:
        """Fallback generic response when no specific topic or trait applies."""
        style_generics: Dict[str, List[str]] = {
            "formal": [
                "I trust this information proves useful to you.",
                "Allow me to elaborate further on the matter.",
            ],
            "mysterious": [
                "I've said too much already. Draw your own conclusions.",
                "Some truths reveal themselves only in time.",
            ],
            "aggressive": [
                "That's all you're getting. Figure out the rest yourself.",
                "I said what I said. Take it or leave it.",
            ],
            "friendly": [
                "I hope that helps! Let me know if you need anything else.",
                "Always happy to chat, {player_name}!",
            ],
            "sarcastic": [
                "I'm sure you'll make excellent use of this information.",
                "Glad I could enlighten you. Truly.",
            ],
            "wise": [
                "Consider carefully what I've told you.",
                "The truth you seek may not be the truth you need.",
            ],
            "humorous": [
                "And that's the story of how I ended up here!",
                "I could tell you more, but I'd have to charge admission.",
            ],
            "melancholic": [
                "Not that it matters much, in the end.",
                "That's how it was, anyway. Different times.",
            ],
        }

        defaults = style_generics.get(npc.style.value, ["I think that covers it."])
        return random.choice(defaults).format(player_name=player_name)

    def _apply_tone(self, text: str, tone: EmotionTone) -> str:
        """Apply emotional tone modifiers to dialogue text."""
        tone_key = tone.value
        prefix_list = _TONE_PREFIXES.get(tone_key, [""])
        adj_list = _TONE_ADJECTIVES.get(tone_key, [""])

        prefix = random.choice(prefix_list) if prefix_list else ""

        if tone != EmotionTone.NEUTRAL and adj_list:
            adj = random.choice(adj_list)
            text = f"({adj}) {text}"

        if prefix:
            text = f"{prefix}{text}"

        return text

    def _apply_speech_patterns(
        self,
        text: str,
        npc: NPCPersonality,
        context_note: str = "",
    ) -> str:
        """Apply NPC-specific speech pattern transformations to dialogue."""
        result = text

        for pattern in npc.speech_patterns:
            if pattern == "verbose":
                transform = _SPEECH_PATTERN_TRANSFORMS.get("verbose", {})
                prefix = transform.get("prefix", "")
                suffix = transform.get("suffix", "")
                result = f"{prefix}{result}{suffix}"

            elif pattern == "terse":
                words = result.split()
                if len(words) > 6:
                    result = " ".join(words[:6]) + "."

            elif pattern == "metaphorical":
                meta_templates = _SPEECH_PATTERN_TRANSFORMS.get("metaphorical", {}).get("metaphors", [])
                if meta_templates:
                    tenor = random.choice(_METAPHOR_TENORS)
                    vehicle = random.choice(_METAPHOR_VEHICLES)
                    metaphor = random.choice(meta_templates).format(tenor=tenor, vehicle=vehicle)
                    if random.random() < 0.5:
                        result = f"{metaphor} {result}"
                    else:
                        result = f"{result} {metaphor}"

            elif pattern == "repetitive":
                transform = _SPEECH_PATTERN_TRANSFORMS.get("repetitive", {})
                echo = transform.get("suffix_template", "")
                if echo:
                    result = f"{result}{echo}"

            elif pattern == "uses slang":
                slang_terms = _SPEECH_PATTERN_TRANSFORMS.get("uses slang", {}).get("slang_terms", [])
                if slang_terms:
                    slang = random.choice(slang_terms)
                    result = result.replace(" is ", f" {slang} ")

            elif pattern == "poetic":
                words = result.split()
                if len(words) >= 3:
                    first_char = words[0][0].lower() if words[0] else ""
                    for i, w in enumerate(words[1:], 1):
                        if w and w[0].lower() == first_char and i > 1:
                            break

            elif pattern == "nervous":
                fillers = _SPEECH_PATTERN_TRANSFORMS.get("nervous", {}).get("fillers", [])
                if fillers:
                    filler = random.choice(fillers)
                    result = f"{filler}, {result}"

            elif pattern == "loud":
                transform = _SPEECH_PATTERN_TRANSFORMS.get("loud", {})
                if transform.get("capitalize"):
                    result = result.upper()
                if transform.get("exclamations"):
                    if not result.endswith("!"):
                        result += "!"

            elif pattern == "quiet":
                transform = _SPEECH_PATTERN_TRANSFORMS.get("quiet", {})
                if transform.get("softeners"):
                    softener = random.choice(transform["softeners"])
                    result = f"{softener}... {result}"
                if transform.get("lowercase"):
                    result = result.lower()

        if context_note:
            result = f"{result} ({context_note})"

        return result

    # ------------------------------------------------------------------
    # Tree Queries
    # ------------------------------------------------------------------

    def get_tree(self, tree_id: str) -> Optional[DialogueTree]:
        """Retrieve a dialogue tree by identifier."""
        return self._dialogue_trees.get(tree_id)

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve an active conversation session."""
        return self._conversations.get(session_id)

    def list_trees(self) -> List[DialogueTree]:
        """Return all registered dialogue trees."""
        return list(self._dialogue_trees.values())

    def list_sessions(self) -> List[ConversationSession]:
        """Return all active conversation sessions."""
        return list(self._conversations.values())

    def end_session(self, session_id: str) -> bool:
        """Terminate a conversation session."""
        with self._lock:
            if session_id in self._conversations:
                del self._conversations[session_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_tree(self, tree_id: str) -> Optional[str]:
        """Export a dialogue tree as a JSON string."""
        tree = self._dialogue_trees.get(tree_id)
        if tree is None:
            return None

        data = {
            "tree": tree.to_dict(),
            "nodes": {nid: node.to_dict() for nid, node in tree.nodes.items()},
            "npc": self._npcs.get(tree.npc_id).to_dict() if tree.npc_id in self._npcs else {},
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_session(self, session_id: str) -> Optional[str]:
        """Export a conversation session as a JSON string."""
        session = self._conversations.get(session_id)
        if session is None:
            return None

        data = {
            "session": session.to_dict(),
            "tree_id": session.dialogue_tree_id,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return engine usage statistics."""
        total_nodes = sum(len(tree.nodes) for tree in self._dialogue_trees.values())
        active_sessions = len(self._conversations)

        style_distribution: Dict[str, int] = {}
        for npc in self._npcs.values():
            s = npc.style.value
            style_distribution[s] = style_distribution.get(s, 0) + 1

        return {
            "total_npcs": len(self._npcs),
            "total_npcs_created": self._total_npcs_created,
            "total_trees": len(self._dialogue_trees),
            "total_trees_created": self._total_trees_created,
            "total_nodes": total_nodes,
            "total_conversations_started": self._total_conversations_started,
            "total_dialogues_generated": self._total_dialogues_generated,
            "active_sessions": active_sessions,
            "style_distribution": style_distribution,
        }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------


def get_dialogue_system() -> DialogueSystemEngine:
    """Get the singleton DialogueSystemEngine instance."""
    return DialogueSystemEngine.get_instance()