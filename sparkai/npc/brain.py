"""
SparkAI NPC - Intelligent NPC Brain
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from sparkai.agent.memory import AgentMemory, MemoryType
from sparkai.agent.llm import LLMProvider
from sparkai.npc.personality import NPCPersonality
from sparkai.npc.behavior import BehaviorTree


class EmotionType(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"


@dataclass
class EmotionalState:
    emotion: EmotionType = EmotionType.NEUTRAL
    intensity: float = 0.5
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.5

    def decay(self, rate: float = 0.01) -> None:
        self.intensity = max(0.0, self.intensity - rate)
        if self.intensity < 0.1:
            self.emotion = EmotionType.NEUTRAL
            self.intensity = 0.0


@dataclass
class AttentionTarget:
    target_id: str = ""
    attention_weight: float = 1.0
    last_known_position: List[float] = field(default_factory=lambda: [0, 0, 0])
    time_since_last_seen: float = 0.0


@dataclass
class NPCGoal:
    name: str = ""
    priority: float = 0.5
    active: bool = True
    progress: float = 0.0


class NPCBrain:
    """
    Neural NPC brain with personality, emotions, memory, and goals.
    Supports LLM-driven decision making and behavior tree execution.
    """

    def __init__(
        self,
        npc_id: str = "",
        personality: Optional[NPCPersonality] = None,
    ):
        self.id = npc_id or str(uuid.uuid4())
        self.personality = personality or NPCPersonality()
        self.memory = AgentMemory()
        self.emotional_state = EmotionalState()
        self.behavior_tree: Optional[BehaviorTree] = None
        self.goals: List[NPCGoal] = []
        self.attention_targets: List[AttentionTarget] = []
        self._llm: Optional[LLMProvider] = None
        self._state = "idle"
        self._dialogue_history: List[Dict[str, str]] = []

    def set_llm_provider(self, provider: LLMProvider) -> None:
        self._llm = provider

    def set_behavior_tree(self, tree: BehaviorTree) -> None:
        self.behavior_tree = tree

    def add_goal(self, name: str, priority: float = 0.5) -> None:
        self.goals.append(NPCGoal(name=name, priority=priority))
        self.goals.sort(key=lambda g: g.priority, reverse=True)

    def remove_goal(self, name: str) -> bool:
        for i, goal in enumerate(self.goals):
            if goal.name == name:
                self.goals.pop(i)
                return True
        return False

    def add_attention_target(self, target_id: str, weight: float = 1.0) -> None:
        self.attention_targets.append(AttentionTarget(target_id=target_id, attention_weight=weight))

    async def decide(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a decision based on personality, emotions, memory, and goals.
        """
        self._state = "thinking"

        if self.behavior_tree:
            bt_result = self.behavior_tree.evaluate()
            if bt_result:
                self._state = "acting"
                return {"action": bt_result, "source": "behavior_tree"}

        if self._llm:
            prompt = self._build_decision_prompt(context)
            response = await self._llm.generate(prompt)
            self._state = "acting"
            return {"action": response, "source": "llm"}

        decision = self._fallback_decide()
        self._state = "acting"
        return {"action": decision, "source": "fallback"}

    async def generate_dialogue(self, player_input: str, context: Optional[Dict] = None) -> str:
        """
        Generate contextual dialogue response.
        """
        if self._llm:
            prompt = self._build_dialogue_prompt(player_input, context)
            response = await self._llm.generate(prompt)
            self._dialogue_history.append({"speaker": "npc", "text": response})
            return response

        personality_desc = f"[{self.personality.name}]" if self.personality.name else "[NPC]"
        return f"{personality_desc} I hear you. Let me think about that..."

    def update_emotion(self, stimulus: str, intensity: float = 0.5) -> None:
        """
        Update emotional state based on stimulus.
        """
        stimulus_lower = stimulus.lower()
        if any(w in stimulus_lower for w in ["happy", "joy", "laugh", "celebrate"]):
            self.emotional_state.emotion = EmotionType.HAPPY
            self.emotional_state.valence = 0.8
        elif any(w in stimulus_lower for w in ["sad", "cry", "loss", "grief"]):
            self.emotional_state.emotion = EmotionType.SAD
            self.emotional_state.valence = -0.7
        elif any(w in stimulus_lower for w in ["angry", "attack", "threat", "enemy"]):
            self.emotional_state.emotion = EmotionType.ANGRY
            self.emotional_state.arousal = 0.8
        elif any(w in stimulus_lower for w in ["scare", "danger", "flee", "monster"]):
            self.emotional_state.emotion = EmotionType.FEARFUL
            self.emotional_state.arousal = 0.9
        elif any(w in stimulus_lower for w in ["surprise", "wow", "unexpected"]):
            self.emotional_state.emotion = EmotionType.SURPRISED
        else:
            self.emotional_state.emotion = EmotionType.NEUTRAL

        self.emotional_state.intensity = min(1.0, intensity)
        self.memory.remember(
            content=f"Emotional stimulus: {stimulus} -> {self.emotional_state.emotion.value}",
            memory_type=MemoryType.EPISODIC,
            importance=0.6,
        )

    def update(self, delta_time: float) -> None:
        self.emotional_state.decay(rate=0.01 * delta_time)
        for target in self.attention_targets:
            target.time_since_last_seen += delta_time
            target.attention_weight = max(0.0, target.attention_weight - 0.01 * delta_time)

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state": self._state,
            "personality": self.personality.to_dict(),
            "emotion": {
                "type": self.emotional_state.emotion.value,
                "intensity": self.emotional_state.intensity,
                "valence": self.emotional_state.valence,
                "arousal": self.emotional_state.arousal,
            },
            "goals": [{"name": g.name, "priority": g.priority, "progress": g.progress} for g in self.goals],
            "memory_size": self.memory.size(),
        }

    def _build_decision_prompt(self, context: Optional[Dict] = None) -> str:
        parts = [
            f"You are {self.personality.name or 'an NPC'} in a game world.",
            f"Personality: {self.personality.to_dict()}",
            f"Current emotion: {self.emotional_state.emotion.value} (intensity: {self.emotional_state.intensity})",
            f"Current goals: {', '.join(g.name for g in self.goals[:3])}",
        ]
        if context:
            parts.append(f"Context: {context}")
        parts.append("What action should you take? Respond with a single action description.")
        return "\n".join(parts)

    def _build_dialogue_prompt(self, player_input: str, context: Optional[Dict] = None) -> str:
        parts = [
            f"You are {self.personality.name or 'an NPC'} speaking to a player.",
            f"Personality traits: {self.personality.to_dict()}",
            f"Emotional state: {self.emotional_state.emotion.value}",
        ]
        if self._dialogue_history:
            recent = self._dialogue_history[-3:]
            parts.append(f"Recent dialogue: {recent}")
        if context:
            parts.append(f"Context: {context}")
        parts.append(f"Player says: {player_input}")
        parts.append("Respond in character:")
        return "\n".join(parts)

    def _fallback_decide(self) -> str:
        if self.goals:
            top_goal = self.goals[0]
            return f"Pursuing goal: {top_goal.name}"
        return "idle"
