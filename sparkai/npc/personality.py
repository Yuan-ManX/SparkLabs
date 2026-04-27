"""
SparkAI NPC - Personality System
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PersonalityTraits:
    courage: float = 0.5
    curiosity: float = 0.5
    aggression: float = 0.3
    friendliness: float = 0.5
    greed: float = 0.3
    honesty: float = 0.7
    patience: float = 0.5
    loyalty: float = 0.6
    intelligence: float = 0.5
    creativity: float = 0.4

    def to_dict(self) -> Dict[str, float]:
        return {
            "courage": self.courage,
            "curiosity": self.curiosity,
            "aggression": self.aggression,
            "friendliness": self.friendliness,
            "greed": self.greed,
            "honesty": self.honesty,
            "patience": self.patience,
            "loyalty": self.loyalty,
            "intelligence": self.intelligence,
            "creativity": self.creativity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "PersonalityTraits":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class NPCPersonality:
    name: str = "NPC"
    traits: PersonalityTraits = field(default_factory=PersonalityTraits)
    background: str = ""
    speech_style: str = "neutral"
    likes: list = field(default_factory=list)
    dislikes: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "traits": self.traits.to_dict(),
            "background": self.background,
            "speech_style": self.speech_style,
            "likes": self.likes,
            "dislikes": self.dislikes,
        }

    def get_dominant_trait(self) -> str:
        trait_values = self.traits.to_dict()
        return max(trait_values, key=trait_values.get)

    def get_relationship_tendency(self) -> str:
        if self.traits.friendliness > 0.7:
            return "ally"
        elif self.traits.aggression > 0.7:
            return "hostile"
        elif self.traits.greed > 0.6:
            return "merchant"
        elif self.traits.loyalty > 0.7:
            return "companion"
        return "neutral"
