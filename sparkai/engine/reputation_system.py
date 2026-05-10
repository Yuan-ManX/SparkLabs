"""
SparkLabs Engine - Faction Reputation System

Multi-dimensional NPC faction relationship management for
AI-native game worlds. Tracks player standing across
faction networks with configurable reputation scales,
relationship decay, faction hierarchies, and behavioral
consequences including NPC hostility levels, trade discounts,
quest availability gating, and dialog options.

Architecture:
  ReputationSystem
    |-- FactionRegistry (faction definitions and relationships)
    |-- ReputationTracker (player-to-faction standing scores)
    |-- RelationshipGraph (inter-faction ally/enemy networks)
    |-- ConsequenceEngine (behavioral effects of reputation)
    |-- DecayManager (reputation drift over time)

Reputation Tiers:
  - EXALTED: maximum positive standing
  - HONORED: trusted ally
  - FRIENDLY: positive standing
  - NEUTRAL: no bias
  - UNFRIENDLY: negative bias
  - HOSTILE: actively opposed
  - AT_WAR: maximum negative standing
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ReputationTier(Enum):
    EXALTED = (3000, "exalted")
    HONORED = (1500, "honored")
    FRIENDLY = (500, "friendly")
    NEUTRAL = (0, "neutral")
    UNFRIENDLY = (-500, "unfriendly")
    HOSTILE = (-1500, "hostile")
    AT_WAR = (-3000, "at_war")

    def __new__(cls, threshold, label):
        obj = object.__new__(cls)
        obj._value_ = label
        obj.threshold = threshold
        return obj


class ConsequenceType(Enum):
    NPC_HOSTILITY = "npc_hostility"
    TRADE_MODIFIER = "trade_modifier"
    QUEST_GATE = "quest_gate"
    DIALOG_ACCESS = "dialog_access"
    GUARD_AGGRESSION = "guard_aggression"
    PRICE_SURCHARGE = "price_surcharge"


class RelationshipType(Enum):
    ALLIED = "allied"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    RIVAL = "rival"
    ENEMY = "enemy"


@dataclass
class FactionDefinition:
    faction_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    color_hex: str = "#888888"
    icon: str = ""
    parent_faction_id: Optional[str] = None
    reputation_decay_rate: float = 0.0
    reputation_floor: float = -3000.0
    reputation_cap: float = 3000.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "faction_id": self.faction_id,
            "name": self.name,
            "color": self.color_hex,
            "parent": self.parent_faction_id,
        }


@dataclass
class InterFactionRelationship:
    faction_a_id: str = ""
    faction_b_id: str = ""
    relationship: RelationshipType = RelationshipType.NEUTRAL
    strength: float = 0.5
    spillover_factor: float = 0.25

    def to_dict(self) -> Dict[str, Any]:
        return {
            "faction_a": self.faction_a_id,
            "faction_b": self.faction_b_id,
            "relationship": self.relationship.value,
            "strength": self.strength,
        }


@dataclass
class ReputationLog:
    log_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    faction_id: str = ""
    amount: float = 0.0
    reason: str = ""
    source: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "faction_id": self.faction_id,
            "amount": round(self.amount, 1),
            "reason": self.reason,
        }


class ReputationSystem:
    _instance: Optional[ReputationSystem] = None

    @classmethod
    def get_instance(cls) -> ReputationSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._factions: Dict[str, FactionDefinition] = {}
        self._player_reputation: Dict[str, float] = {}
        self._inter_faction: Dict[str, Dict[str, InterFactionRelationship]] = {}
        self._reputation_log: List[ReputationLog] = []
        self._total_factions: int = 0

    def create_faction(self, faction_id: str, name: str, description: str = "",
                       color_hex: str = "#888888", parent_id: Optional[str] = None) -> FactionDefinition:
        faction = FactionDefinition(
            faction_id=faction_id, name=name, description=description,
            color_hex=color_hex, parent_faction_id=parent_id,
        )
        self._factions[faction_id] = faction
        self._player_reputation[faction_id] = 0.0
        self._total_factions += 1
        return faction

    def set_relationship(self, faction_a: str, faction_b: str,
                         relationship: RelationshipType, strength: float = 0.5,
                         spillover: float = 0.25):
        key = f"{min(faction_a, faction_b)}_{max(faction_a, faction_b)}"
        rel = InterFactionRelationship(
            faction_a_id=faction_a, faction_b_id=faction_b,
            relationship=relationship, strength=strength, spillover_factor=spillover,
        )
        if faction_a not in self._inter_faction:
            self._inter_faction[faction_a] = {}
        if faction_b not in self._inter_faction:
            self._inter_faction[faction_b] = {}
        self._inter_faction[faction_a][faction_b] = rel
        self._inter_faction[faction_b][faction_a] = rel

    def modify_reputation(self, faction_id: str, amount: float, reason: str = "",
                          source: str = "system", propagate: bool = True) -> float:
        faction = self._factions.get(faction_id)
        if faction is None:
            return 0.0

        current = self._player_reputation.get(faction_id, 0.0)
        new_value = max(faction.reputation_floor, min(faction.reputation_cap, current + amount))
        self._player_reputation[faction_id] = new_value

        log = ReputationLog(faction_id=faction_id, amount=amount, reason=reason, source=source)
        self._reputation_log.append(log)
        if len(self._reputation_log) > 200:
            self._reputation_log = self._reputation_log[-200:]

        if propagate:
            self._propagate_spillover(faction_id, amount)

        return new_value

    def _propagate_spillover(self, faction_id: str, base_amount: float):
        related = self._inter_faction.get(faction_id, {})
        for other_id, rel in related.items():
            factor = {
                RelationshipType.ALLIED: 0.5,
                RelationshipType.FRIENDLY: 0.3,
                RelationshipType.NEUTRAL: 0.0,
                RelationshipType.RIVAL: -0.2,
                RelationshipType.ENEMY: -0.4,
            }
            spill = base_amount * rel.spillover_factor * factor.get(rel.relationship, 0.0)
            if abs(spill) > 1:
                faction = self._factions.get(other_id)
                if faction:
                    current = self._player_reputation.get(other_id, 0.0)
                    new_val = max(faction.reputation_floor, min(faction.reputation_cap, current + spill))
                    self._player_reputation[other_id] = new_val

    def get_reputation_tier(self, faction_id: str) -> ReputationTier:
        score = self._player_reputation.get(faction_id, 0)
        tiers = sorted(ReputationTier, key=lambda t: t.threshold, reverse=True)
        for tier in tiers:
            if score >= tier.threshold:
                return tier
        return ReputationTier.AT_WAR

    def get_trade_modifier(self, faction_id: str) -> float:
        tier = self.get_reputation_tier(faction_id)
        modifiers = {
            ReputationTier.EXALTED: 0.80,
            ReputationTier.HONORED: 0.90,
            ReputationTier.FRIENDLY: 0.95,
            ReputationTier.NEUTRAL: 1.00,
            ReputationTier.UNFRIENDLY: 1.10,
            ReputationTier.HOSTILE: 1.30,
            ReputationTier.AT_WAR: -1.0,
        }
        return modifiers.get(tier, 1.0)

    def update_decay(self, faction_id: str, delta_time: float):
        faction = self._factions.get(faction_id)
        if faction is None or faction.reputation_decay_rate == 0:
            return
        current = self._player_reputation.get(faction_id, 0)
        if current > 0:
            decay = -faction.reputation_decay_rate * delta_time
        elif current < 0:
            decay = faction.reputation_decay_rate * delta_time
        else:
            return
        new_val = max(faction.reputation_floor, min(faction.reputation_cap, current + decay))
        self._player_reputation[faction_id] = new_val

    def get_player_standing_summary(self) -> List[Dict[str, Any]]:
        summaries = []
        for fid, score in self._player_reputation.items():
            faction = self._factions.get(fid)
            if faction:
                summaries.append({
                    "faction_id": fid,
                    "name": faction.name,
                    "score": round(score, 1),
                    "tier": self.get_reputation_tier(fid).value,
                    "trade_modifier": self.get_trade_modifier(fid),
                })
        summaries.sort(key=lambda s: s["score"], reverse=True)
        return summaries

    def get_faction_statistics(self) -> List[Dict[str, Any]]:
        stats = []
        for fid, faction in self._factions.items():
            score = self._player_reputation.get(fid, 0)
            allies = sum(1 for rel in self._inter_faction.get(fid, {}).values()
                        if rel.relationship == RelationshipType.ALLIED)
            enemies = sum(1 for rel in self._inter_faction.get(fid, {}).values()
                         if rel.relationship == RelationshipType.ENEMY)
            stats.append({
                "faction_id": fid,
                "name": faction.name,
                "score": round(score, 1),
                "tier": self.get_reputation_tier(fid).value,
                "allies": allies,
                "enemies": enemies,
            })
        return stats

    def get_consequences(self, faction_id: str) -> Dict[str, Any]:
        tier = self.get_reputation_tier(faction_id)
        trade = self.get_trade_modifier(faction_id)
        return {
            "faction_id": faction_id,
            "tier": tier.value,
            "trade_modifier": trade,
            "can_trade": trade > 0,
            "npc_aggression": tier in (ReputationTier.HOSTILE, ReputationTier.AT_WAR),
            "quests_available": tier.threshold >= ReputationTier.NEUTRAL.threshold,
            "special_dialog": tier in (ReputationTier.EXALTED, ReputationTier.AT_WAR),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_factions": self._total_factions,
            "active_factions": len(self._factions),
            "relationships": sum(len(rels) for rels in self._inter_faction.values()) // 2,
            "reputation_entries": len(self._player_reputation),
            "tier_distribution": {
                tier.value: sum(1 for fid in self._factions if self.get_reputation_tier(fid) == tier)
                for tier in ReputationTier
            },
        }


def get_reputation_system() -> ReputationSystem:
    return ReputationSystem.get_instance()