"""
SparkLabs Engine - Achievement System Engine

An AI-driven achievement system for the AI-native game engine that
designs achievements, tracks player progress, unlocks rewards, and
generates achievement-based engagement. Supports category-based
generation, personalized recommendations, milestone creation, and
leaderboard compilation.

Architecture:
  AchievementSystemEngine (singleton)
    |-- AchievementDefinition (template for an unlockable achievement)
    |-- PlayerAchievement (per-player progress tracking record)
    |-- AchievementNotification (unlock event with reward details)
    |-- AchievementCategory (10 thematic achievement categories)
    |-- AchievementRarity (6 rarity tiers from common to mythic)
    |-- AchievementStatus (lifecycle: locked -> in_progress -> unlocked -> claimed)

Core Capabilities:
  - create_achievement: Define a new achievement with rewards and conditions
  - update_progress: Increment a player's progress toward a specific achievement
  - check_unlocks: Evaluate all in-progress achievements for new completions
  - claim_reward: Collect the reward for an unlocked but unclaimed achievement
  - get_player_achievements: Retrieve all achievement records for a player
  - get_player_stats: Aggregate stats and completion metrics for a player
  - generate_achievements_for_category: AI-driven batch creation per category
  - recommend_achievements: Suggest achievements the player is close to finishing
  - generate_milestone_achievements: Create personalized milestone challenges
  - get_leaderboard: Rank players by achievement points within a category
  - get_stats: Global engine statistics and health summary
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AchievementCategory(Enum):
    """Thematic classification for achievements."""
    COMBAT = "combat"
    EXPLORATION = "exploration"
    COLLECTION = "collection"
    PROGRESSION = "progression"
    SOCIAL = "social"
    MASTERY = "mastery"
    CHALLENGE = "challenge"
    STORY = "story"
    SECRET = "secret"
    MILESTONE = "milestone"


class AchievementRarity(Enum):
    """Rarity tier determining visual treatment and reward scaling."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class AchievementStatus(Enum):
    """Lifecycle states for a player-achievement relationship."""
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    UNLOCKED = "unlocked"
    CLAIMED = "claimed"


# ---------------------------------------------------------------------------
# Rarity Configuration
# ---------------------------------------------------------------------------

RARITY_MULTIPLIERS: Dict[AchievementRarity, float] = {
    AchievementRarity.COMMON: 1.0,
    AchievementRarity.UNCOMMON: 1.5,
    AchievementRarity.RARE: 2.5,
    AchievementRarity.EPIC: 4.0,
    AchievementRarity.LEGENDARY: 7.0,
    AchievementRarity.MYTHIC: 12.0,
}

RARITY_COLORS: Dict[AchievementRarity, str] = {
    AchievementRarity.COMMON: "#9d9d9d",
    AchievementRarity.UNCOMMON: "#1eff00",
    AchievementRarity.RARE: "#0070dd",
    AchievementRarity.EPIC: "#a335ee",
    AchievementRarity.LEGENDARY: "#ff8000",
    AchievementRarity.MYTHIC: "#e6cc80",
}

RARITY_WEIGHTS: Dict[AchievementRarity, float] = {
    AchievementRarity.COMMON: 50.0,
    AchievementRarity.UNCOMMON: 30.0,
    AchievementRarity.RARE: 12.0,
    AchievementRarity.EPIC: 5.0,
    AchievementRarity.LEGENDARY: 2.0,
    AchievementRarity.MYTHIC: 1.0,
}


# ---------------------------------------------------------------------------
# Category Templates for AI-driven Generation
# ---------------------------------------------------------------------------

CATEGORY_TEMPLATES: Dict[AchievementCategory, List[Dict[str, Any]]] = {
    AchievementCategory.COMBAT: [
        {"name": "First Blood", "description": "Defeat your first enemy", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Seasoned Warrior", "description": "Defeat {n} enemies in total", "target": 100, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Battle Hardened", "description": "Defeat {n} enemies in total", "target": 500, "rarity": AchievementRarity.RARE},
        {"name": "One-Person Army", "description": "Defeat {n} enemies in total", "target": 2000, "rarity": AchievementRarity.EPIC},
        {"name": "Exterminator", "description": "Defeat {n} enemies in total", "target": 10000, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Combo Novice", "description": "Achieve a {n}-hit combo", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Combo Artist", "description": "Achieve a {n}-hit combo", "target": 50, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Combo Master", "description": "Achieve a {n}-hit combo", "target": 100, "rarity": AchievementRarity.RARE},
        {"name": "Combo God", "description": "Achieve a {n}-hit combo", "target": 500, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Heavy Hitter", "description": "Deal {n} total damage", "target": 10000, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Devastator", "description": "Deal {n} total damage", "target": 100000, "rarity": AchievementRarity.RARE},
        {"name": "World Breaker", "description": "Deal {n} total damage", "target": 1000000, "rarity": AchievementRarity.EPIC},
        {"name": "Boss Slayer", "description": "Defeat {n} boss enemies", "target": 10, "rarity": AchievementRarity.RARE},
        {"name": "Boss Hunter", "description": "Defeat {n} boss enemies", "target": 50, "rarity": AchievementRarity.EPIC},
        {"name": "Untouchable", "description": "Complete a battle without taking damage", "target": 1, "rarity": AchievementRarity.RARE},
        {"name": "Perfect Defense", "description": "Block {n} attacks in a single fight", "target": 20, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Critical Mass", "description": "Land {n} critical hits", "target": 100, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Lethal Precision", "description": "Land {n} critical hits", "target": 1000, "rarity": AchievementRarity.EPIC},
        {"name": "Flawless Victory", "description": "Win {n} battles with full health", "target": 50, "rarity": AchievementRarity.RARE},
        {"name": "Deathless Run", "description": "Defeat {n} enemies without dying", "target": 100, "rarity": AchievementRarity.EPIC},
    ],
    AchievementCategory.EXPLORATION: [
        {"name": "First Steps", "description": "Discover your first area", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Wanderer", "description": "Discover {n} unique areas", "target": 10, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Pathfinder", "description": "Discover {n} unique areas", "target": 30, "rarity": AchievementRarity.RARE},
        {"name": "Cartographer", "description": "Discover {n} unique areas", "target": 100, "rarity": AchievementRarity.EPIC},
        {"name": "World Traveler", "description": "Travel {n} total distance", "target": 10000, "rarity": AchievementRarity.COMMON},
        {"name": "Marathon Runner", "description": "Travel {n} total distance", "target": 100000, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Globe Trotter", "description": "Travel {n} total distance", "target": 1000000, "rarity": AchievementRarity.EPIC},
        {"name": "Secret Finder", "description": "Discover {n} hidden locations", "target": 5, "rarity": AchievementRarity.RARE},
        {"name": "Secret Hunter", "description": "Discover {n} hidden locations", "target": 25, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Every Corner", "description": "Reveal {n} percent of the map", "target": 100, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Waypoint Unlocker", "description": "Activate {n} waypoints", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Fast Travel Network", "description": "Activate {n} waypoints", "target": 50, "rarity": AchievementRarity.UNCOMMON},
        {"name": "High Climber", "description": "Reach {n} elevated vantage points", "target": 20, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Deep Diver", "description": "Explore {n} underground zones", "target": 10, "rarity": AchievementRarity.RARE},
        {"name": "Portal Hopper", "description": "Use portals or teleports {n} times", "target": 50, "rarity": AchievementRarity.COMMON},
    ],
    AchievementCategory.COLLECTION: [
        {"name": "Collector's Start", "description": "Collect {n} unique items", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Avid Collector", "description": "Collect {n} unique items", "target": 100, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Hoarder", "description": "Collect {n} unique items", "target": 500, "rarity": AchievementRarity.RARE},
        {"name": "Completionist", "description": "Collect {n} unique items", "target": 1000, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Set Collector", "description": "Complete {n} item sets", "target": 1, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Set Enthusiast", "description": "Complete {n} item sets", "target": 10, "rarity": AchievementRarity.RARE},
        {"name": "Set Master", "description": "Complete {n} item sets", "target": 50, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Treasure Hunter", "description": "Open {n} treasure chests", "target": 20, "rarity": AchievementRarity.COMMON},
        {"name": "Treasure Raider", "description": "Open {n} treasure chests", "target": 100, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Treasure Legend", "description": "Open {n} treasure chests", "target": 500, "rarity": AchievementRarity.EPIC},
        {"name": "Rare Find", "description": "Obtain {n} rare or better items", "target": 10, "rarity": AchievementRarity.RARE},
        {"name": "Epic Loot", "description": "Obtain {n} epic or better items", "target": 5, "rarity": AchievementRarity.EPIC},
        {"name": "Mythic Hoard", "description": "Obtain {n} mythic items", "target": 1, "rarity": AchievementRarity.MYTHIC},
        {"name": "Currency Baron", "description": "Accumulate {n} total currency", "target": 10000, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Currency Magnate", "description": "Accumulate {n} total currency", "target": 1000000, "rarity": AchievementRarity.LEGENDARY},
    ],
    AchievementCategory.PROGRESSION: [
        {"name": "Getting Started", "description": "Reach level {n}", "target": 5, "rarity": AchievementRarity.COMMON},
        {"name": "Rising Star", "description": "Reach level {n}", "target": 25, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Veteran", "description": "Reach level {n}", "target": 50, "rarity": AchievementRarity.RARE},
        {"name": "Elite", "description": "Reach level {n}", "target": 75, "rarity": AchievementRarity.EPIC},
        {"name": "Max Level", "description": "Reach level {n}", "target": 100, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Quest Beginner", "description": "Complete {n} quests", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Quest Enthusiast", "description": "Complete {n} quests", "target": 50, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Quest Master", "description": "Complete {n} quests", "target": 200, "rarity": AchievementRarity.RARE},
        {"name": "Quest Legend", "description": "Complete {n} quests", "target": 500, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Story Arc I", "description": "Complete chapter {n} of the main story", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Story Arc V", "description": "Complete chapter {n} of the main story", "target": 5, "rarity": AchievementRarity.RARE},
        {"name": "Side Quest Hero", "description": "Complete {n} side quests", "target": 25, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Daily Grinder", "description": "Complete {n} daily quests", "target": 30, "rarity": AchievementRarity.COMMON},
        {"name": "Daily Devotee", "description": "Complete {n} daily quests", "target": 365, "rarity": AchievementRarity.LEGENDARY},
    ],
    AchievementCategory.SOCIAL: [
        {"name": "Making Friends", "description": "Add {n} friends", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Social Butterfly", "description": "Add {n} friends", "target": 50, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Party Starter", "description": "Join {n} group activities", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Team Player", "description": "Join {n} group activities", "target": 100, "rarity": AchievementRarity.RARE},
        {"name": "Guild Member", "description": "Join or create a guild", "target": 1, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Guild Leader", "description": "Lead a guild with {n} members", "target": 50, "rarity": AchievementRarity.EPIC},
        {"name": "Helper", "description": "Assist {n} other players", "target": 10, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Mentor", "description": "Assist {n} other players", "target": 100, "rarity": AchievementRarity.RARE},
        {"name": "Trade Starter", "description": "Complete {n} trades", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Market Mogul", "description": "Complete {n} trades", "target": 500, "rarity": AchievementRarity.EPIC},
        {"name": "Gift Giver", "description": "Send {n} gifts to other players", "target": 25, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Co-op Champion", "description": "Complete {n} co-op missions", "target": 50, "rarity": AchievementRarity.RARE},
    ],
    AchievementCategory.MASTERY: [
        {"name": "Skill Up", "description": "Max out {n} skill", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Skill Specialist", "description": "Max out {n} skills", "target": 5, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Skill Grandmaster", "description": "Max out {n} skills", "target": 20, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Perfect Run", "description": "Complete {n} missions with perfect rating", "target": 1, "rarity": AchievementRarity.RARE},
        {"name": "Perfectionist", "description": "Complete {n} missions with perfect rating", "target": 25, "rarity": AchievementRarity.EPIC},
        {"name": "Speed Demon", "description": "Complete a mission in under {n} seconds", "target": 60, "rarity": AchievementRarity.RARE},
        {"name": "Speed Runner", "description": "Complete {n} speed-run challenges", "target": 10, "rarity": AchievementRarity.EPIC},
        {"name": "No Damage Run", "description": "Complete {n} missions without taking damage", "target": 5, "rarity": AchievementRarity.EPIC},
        {"name": "Minimalist", "description": "Complete a mission using only {n} items", "target": 3, "rarity": AchievementRarity.RARE},
        {"name": "One Trick Pony", "description": "Defeat a boss using only one ability type", "target": 1, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Style Master", "description": "Earn an S-rank on {n} missions", "target": 10, "rarity": AchievementRarity.RARE},
        {"name": "All-Rounder", "description": "Deal damage with {n} different damage types", "target": 5, "rarity": AchievementRarity.UNCOMMON},
    ],
    AchievementCategory.CHALLENGE: [
        {"name": "Challenge Accepted", "description": "Complete {n} challenge mode missions", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Challenge Seeker", "description": "Complete {n} challenge mode missions", "target": 25, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Challenge Conqueror", "description": "Complete {n} challenge mode missions", "target": 100, "rarity": AchievementRarity.EPIC},
        {"name": "Hard Mode Clear", "description": "Complete the game on hard difficulty", "target": 1, "rarity": AchievementRarity.RARE},
        {"name": "Nightmare Clear", "description": "Complete the game on the hardest difficulty", "target": 1, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Ironman", "description": "Reach level {n} without dying once", "target": 30, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Pacifist", "description": "Complete a mission defeating only {n} enemies", "target": 0, "rarity": AchievementRarity.RARE},
        {"name": "Speed Record", "description": "Set a personal best under {n} seconds", "target": 300, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Endurance", "description": "Survive for {n} minutes in survival mode", "target": 30, "rarity": AchievementRarity.RARE},
        {"name": "Marathon Survivor", "description": "Survive for {n} minutes in survival mode", "target": 120, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Time Trial Gold", "description": "Earn gold in {n} time trials", "target": 10, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Gauntlet Runner", "description": "Complete the boss gauntlet in {n} minutes", "target": 15, "rarity": AchievementRarity.EPIC},
    ],
    AchievementCategory.STORY: [
        {"name": "The Beginning", "description": "Complete the prologue", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "The Journey", "description": "Complete act {n}", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Midpoint", "description": "Complete act {n}", "target": 3, "rarity": AchievementRarity.UNCOMMON},
        {"name": "The Climax", "description": "Complete act {n}", "target": 5, "rarity": AchievementRarity.RARE},
        {"name": "The End", "description": "Complete the main story", "target": 1, "rarity": AchievementRarity.EPIC},
        {"name": "Lore Keeper", "description": "Find {n} lore entries", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Lore Scholar", "description": "Find {n} lore entries", "target": 100, "rarity": AchievementRarity.RARE},
        {"name": "Lore Master", "description": "Find all {n} lore entries", "target": 250, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Dialogue Explorer", "description": "Exhaust {n} NPC dialogue trees", "target": 20, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Cutscene Watcher", "description": "Watch {n} cutscenes", "target": 15, "rarity": AchievementRarity.COMMON},
        {"name": "Alternate Ending", "description": "Unlock an alternate ending", "target": 1, "rarity": AchievementRarity.RARE},
        {"name": "All Endings", "description": "Unlock all {n} endings", "target": 3, "rarity": AchievementRarity.LEGENDARY},
    ],
    AchievementCategory.SECRET: [
        {"name": "Hidden Path", "description": "Discover a secret passage", "target": 1, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Easter Egg Hunter", "description": "Find {n} easter eggs", "target": 5, "rarity": AchievementRarity.RARE},
        {"name": "Code Breaker", "description": "Solve {n} hidden puzzles", "target": 3, "rarity": AchievementRarity.RARE},
        {"name": "Behind the Curtain", "description": "Access a developer room", "target": 1, "rarity": AchievementRarity.EPIC},
        {"name": "The Forgotten", "description": "Discover a hidden boss encounter", "target": 1, "rarity": AchievementRarity.EPIC},
        {"name": "Secret Ending", "description": "Unlock the true ending", "target": 1, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Glitch in the Matrix", "description": "Trigger a rare world event", "target": 1, "rarity": AchievementRarity.MYTHIC},
    ],
    AchievementCategory.MILESTONE: [
        {"name": "Playtime: 1 Hour", "description": "Play for {n} total hour", "target": 1, "rarity": AchievementRarity.COMMON},
        {"name": "Playtime: 10 Hours", "description": "Play for {n} total hours", "target": 10, "rarity": AchievementRarity.COMMON},
        {"name": "Playtime: 100 Hours", "description": "Play for {n} total hours", "target": 100, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Playtime: 500 Hours", "description": "Play for {n} total hours", "target": 500, "rarity": AchievementRarity.RARE},
        {"name": "Playtime: 1000 Hours", "description": "Play for {n} total hours", "target": 1000, "rarity": AchievementRarity.EPIC},
        {"name": "Login Streak 7", "description": "Log in {n} days in a row", "target": 7, "rarity": AchievementRarity.COMMON},
        {"name": "Login Streak 30", "description": "Log in {n} days in a row", "target": 30, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Login Streak 365", "description": "Log in {n} days in a row", "target": 365, "rarity": AchievementRarity.LEGENDARY},
        {"name": "Account Anniversary", "description": "Reach your {n}-year anniversary", "target": 1, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Total Score", "description": "Accumulate {n} total achievement points", "target": 100, "rarity": AchievementRarity.COMMON},
        {"name": "Score Hunter", "description": "Accumulate {n} total achievement points", "target": 1000, "rarity": AchievementRarity.UNCOMMON},
        {"name": "Score Master", "description": "Accumulate {n} total achievement points", "target": 5000, "rarity": AchievementRarity.EPIC},
        {"name": "Score Legend", "description": "Accumulate {n} total achievement points", "target": 10000, "rarity": AchievementRarity.LEGENDARY},
    ],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AchievementDefinition:
    """Blueprint for an achievement that can be unlocked by players."""
    def_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    category: AchievementCategory = AchievementCategory.MILESTONE
    rarity: AchievementRarity = AchievementRarity.COMMON
    icon: str = ""
    target_value: float = 1.0
    reward_exp: int = 0
    reward_currency: int = 0
    reward_items: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    is_hidden: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "def_id": self.def_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "rarity": self.rarity.value,
            "icon": self.icon,
            "target_value": self.target_value,
            "reward_exp": self.reward_exp,
            "reward_currency": self.reward_currency,
            "reward_items": self.reward_items,
            "is_hidden": self.is_hidden,
            "created_at": self.created_at,
        }


@dataclass
class PlayerAchievement:
    """Tracks a single player's progress toward a specific achievement."""
    pa_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    player_id: str = ""
    def_id: str = ""
    status: AchievementStatus = AchievementStatus.LOCKED
    current_progress: float = 0.0
    target_value: float = 1.0
    unlocked_at: Optional[float] = None
    claimed_at: Optional[float] = None

    def progress_percent(self) -> float:
        if self.target_value <= 0:
            return 100.0
        return min(100.0, (self.current_progress / self.target_value) * 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pa_id": self.pa_id,
            "player_id": self.player_id,
            "def_id": self.def_id,
            "status": self.status.value,
            "current_progress": self.current_progress,
            "target_value": self.target_value,
            "progress_percent": self.progress_percent(),
            "unlocked_at": self.unlocked_at,
            "claimed_at": self.claimed_at,
        }


@dataclass
class AchievementNotification:
    """Notification payload sent when an achievement is unlocked."""
    notif_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    player_id: str = ""
    achievement_name: str = ""
    rarity: AchievementRarity = AchievementRarity.COMMON
    description: str = ""
    reward_exp: int = 0
    reward_currency: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notif_id": self.notif_id,
            "player_id": self.player_id,
            "achievement_name": self.achievement_name,
            "rarity": self.rarity.value,
            "description": self.description,
            "reward_exp": self.reward_exp,
            "reward_currency": self.reward_currency,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Achievement System Engine (Singleton)
# ---------------------------------------------------------------------------


class AchievementSystemEngine:
    """AI-driven achievement orchestration engine."""

    _instance: Optional["AchievementSystemEngine"] = None
    _lock: threading.RLock = threading.RLock()

    RECOMMENDATION_THRESHOLD: float = 70.0
    MAX_NOTIFICATION_HISTORY: int = 500
    DEFAULT_LEADERBOARD_LIMIT: int = 50

    def __new__(cls) -> "AchievementSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AchievementSystemEngine":
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._definitions: Dict[str, AchievementDefinition] = {}
        self._player_achievements: Dict[str, Dict[str, PlayerAchievement]] = defaultdict(dict)
        self._notifications: deque = deque(maxlen=self.MAX_NOTIFICATION_HISTORY)
        self._player_stats_cache: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._unlock_order_counter: int = 0
        self._total_achievements_created: int = 0
        self._total_unlocks: int = 0
        self._total_claimed: int = 0

    # ------------------------------------------------------------------
    # Achievement Definition Management
    # ------------------------------------------------------------------

    def create_achievement(
        self,
        name: str,
        description: str,
        category: AchievementCategory,
        rarity: AchievementRarity,
        target_value: float = 1.0,
        reward_exp: int = 0,
        reward_currency: int = 0,
        reward_items: Optional[List[str]] = None,
        is_hidden: bool = False,
    ) -> AchievementDefinition:
        """Create and register a new achievement definition."""
        with self._lock:
            rarity_mult = RARITY_MULTIPLIERS.get(rarity, 1.0)

            if reward_exp == 0:
                reward_exp = int(target_value * 10 * rarity_mult)
            if reward_currency == 0:
                reward_currency = int(target_value * 5 * rarity_mult)

            definition = AchievementDefinition(
                name=name,
                description=description,
                category=category,
                rarity=rarity,
                icon=f"icon_{category.value}_{rarity.value}",
                target_value=target_value,
                reward_exp=reward_exp,
                reward_currency=reward_currency,
                reward_items=reward_items or [],
                is_hidden=is_hidden,
                conditions={
                    "stat_key": f"stat_{category.value}_{name.lower().replace(' ', '_')}",
                    "target_value": target_value,
                },
            )
            self._definitions[definition.def_id] = definition
            self._total_achievements_created += 1
            return definition

    def get_definition(self, def_id: str) -> Optional[AchievementDefinition]:
        """Retrieve an achievement definition by id."""
        return self._definitions.get(def_id)

    def get_all_definitions(self) -> List[AchievementDefinition]:
        """Retrieve all registered achievement definitions."""
        return list(self._definitions.values())

    # ------------------------------------------------------------------
    # Progress Tracking
    # ------------------------------------------------------------------

    def update_progress(
        self,
        player_id: str,
        def_id: str,
        progress_increment: float = 1.0,
    ) -> Optional[PlayerAchievement]:
        """Increment a player's progress toward an achievement.

        Returns the updated PlayerAchievement, or None if the definition
        does not exist.
        """
        definition = self._definitions.get(def_id)
        if definition is None:
            return None

        with self._lock:
            pa = self._ensure_player_achievement(player_id, def_id, definition)

            if pa.status in (AchievementStatus.CLAIMED,):
                return pa

            pa.current_progress += progress_increment

            if pa.current_progress >= pa.target_value:
                pa.current_progress = pa.target_value
                if pa.status != AchievementStatus.UNLOCKED:
                    pa.status = AchievementStatus.UNLOCKED
                    pa.unlocked_at = time.time()
                    self._unlock_order_counter += 1
                    self._total_unlocks += 1
            elif pa.current_progress > 0 and pa.status == AchievementStatus.LOCKED:
                pa.status = AchievementStatus.IN_PROGRESS

            return pa

    def _ensure_player_achievement(
        self,
        player_id: str,
        def_id: str,
        definition: AchievementDefinition,
    ) -> PlayerAchievement:
        """Get or create a PlayerAchievement record for a player-definition pair."""
        player_records = self._player_achievements[player_id]
        if def_id not in player_records:
            player_records[def_id] = PlayerAchievement(
                player_id=player_id,
                def_id=def_id,
                target_value=definition.target_value,
            )
        return player_records[def_id]

    # ------------------------------------------------------------------
    # Unlock Checking
    # ------------------------------------------------------------------

    def check_unlocks(self, player_id: str) -> List[AchievementNotification]:
        """Evaluate all tracked achievements for a player and generate
        notifications for any that just became unlocked.

        Returns a list of AchievementNotification objects for newly
        unlocked achievements.
        """
        notifications: List[AchievementNotification] = []

        with self._lock:
            player_records = self._player_achievements.get(player_id, {})
            for def_id, pa in list(player_records.items()):
                if pa.status != AchievementStatus.UNLOCKED:
                    continue

                definition = self._definitions.get(def_id)
                if definition is None:
                    continue

                notification = AchievementNotification(
                    player_id=player_id,
                    achievement_name=definition.name,
                    rarity=definition.rarity,
                    description=definition.description,
                    reward_exp=definition.reward_exp,
                    reward_currency=definition.reward_currency,
                )
                notifications.append(notification)
                self._notifications.append(notification)

        return notifications

    # ------------------------------------------------------------------
    # Reward Claiming
    # ------------------------------------------------------------------

    def claim_reward(self, player_id: str, def_id: str) -> Optional[PlayerAchievement]:
        """Claim the reward for an unlocked achievement.

        Transitions the achievement status from UNLOCKED to CLAIMED.
        Returns the updated PlayerAchievement, or None if not eligible.
        """
        with self._lock:
            player_records = self._player_achievements.get(player_id, {})
            pa = player_records.get(def_id)
            if pa is None:
                return None
            if pa.status != AchievementStatus.UNLOCKED:
                return None

            pa.status = AchievementStatus.CLAIMED
            pa.claimed_at = time.time()
            self._total_claimed += 1

            return pa

    # ------------------------------------------------------------------
    # Player Queries
    # ------------------------------------------------------------------

    def get_player_achievements(self, player_id: str) -> List[PlayerAchievement]:
        """Retrieve all achievement records for a given player."""
        with self._lock:
            records = self._player_achievements.get(player_id, {})
            return list(records.values())

    def get_player_stats(self, player_id: str) -> Dict[str, Any]:
        """Compute aggregate statistics for a player's achievement progress."""
        with self._lock:
            records = self._player_achievements.get(player_id, {})
            total = len(records)
            unlocked = sum(1 for pa in records.values() if pa.status == AchievementStatus.UNLOCKED)
            claimed = sum(1 for pa in records.values() if pa.status == AchievementStatus.CLAIMED)
            in_progress = sum(1 for pa in records.values() if pa.status == AchievementStatus.IN_PROGRESS)
            locked = sum(1 for pa in records.values() if pa.status == AchievementStatus.LOCKED)

            category_counts: Dict[str, int] = defaultdict(int)
            rarity_counts: Dict[str, int] = defaultdict(int)
            total_points = 0
            total_exp = 0
            total_currency = 0

            for def_id, pa in records.items():
                definition = self._definitions.get(def_id)
                if definition is None:
                    continue
                if pa.status in (AchievementStatus.UNLOCKED, AchievementStatus.CLAIMED):
                    category_counts[definition.category.value] += 1
                    rarity_counts[definition.rarity.value] += 1
                    total_points += int(definition.target_value * RARITY_MULTIPLIERS.get(definition.rarity, 1.0))
                    total_exp += definition.reward_exp
                    total_currency += definition.reward_currency

            completion_pct = (unlocked + claimed) / total * 100 if total > 0 else 0.0

            return {
                "player_id": player_id,
                "total_achievements": total,
                "locked": locked,
                "in_progress": in_progress,
                "unlocked": unlocked,
                "claimed": claimed,
                "completion_percent": round(completion_pct, 2),
                "total_points": total_points,
                "total_exp_earned": total_exp,
                "total_currency_earned": total_currency,
                "by_category": dict(category_counts),
                "by_rarity": dict(rarity_counts),
            }

    # ------------------------------------------------------------------
    # AI-driven Achievement Generation
    # ------------------------------------------------------------------

    def generate_achievements_for_category(
        self,
        category: AchievementCategory,
        count: int = 5,
    ) -> List[AchievementDefinition]:
        """Generate a batch of fitting achievements for a given category.

        Uses internal templates and procedural variation to create
        category-appropriate achievements with scaled targets and rewards.
        """
        templates = CATEGORY_TEMPLATES.get(category, [])
        if not templates:
            templates = CATEGORY_TEMPLATES[AchievementCategory.MILESTONE]

        generated: List[AchievementDefinition] = []
        available = list(templates)

        with self._lock:
            for _ in range(min(count, len(available))):
                if not available:
                    break

                idx = random.randint(0, len(available) - 1)
                template = available.pop(idx)

                rarity = template.get("rarity", AchievementRarity.COMMON)
                target = template.get("target", 1)

                jitter = 1.0
                if category == AchievementCategory.COMBAT:
                    jitter = random.uniform(0.9, 1.3)
                elif category == AchievementCategory.EXPLORATION:
                    jitter = random.uniform(0.85, 1.2)
                elif category == AchievementCategory.COLLECTION:
                    jitter = random.uniform(0.8, 1.4)
                elif category == AchievementCategory.CHALLENGE:
                    jitter = random.uniform(0.7, 1.1)

                adjusted_target = max(1, int(target * jitter))
                rarity_mult = RARITY_MULTIPLIERS.get(rarity, 1.0)

                name = template["name"].replace("{n}", str(adjusted_target))
                description = template["description"].replace("{n}", str(adjusted_target))

                definition = self.create_achievement(
                    name=name,
                    description=description,
                    category=category,
                    rarity=rarity,
                    target_value=float(adjusted_target),
                    reward_exp=int(adjusted_target * 10 * rarity_mult),
                    reward_currency=int(adjusted_target * 5 * rarity_mult),
                )
                generated.append(definition)

        return generated

    def recommend_achievements(
        self,
        player_id: str,
        max_recommendations: int = 5,
    ) -> List[AchievementDefinition]:
        """Suggest achievements the player is close to completing.

        Scans all in-progress achievements and returns those with progress
        above the recommendation threshold, sorted by proximity to completion.
        """
        recommendations: List[Tuple[float, AchievementDefinition]] = []

        with self._lock:
            player_records = self._player_achievements.get(player_id, {})
            for def_id, pa in player_records.items():
                if pa.status != AchievementStatus.IN_PROGRESS:
                    continue
                pct = pa.progress_percent()
                if pct < self.RECOMMENDATION_THRESHOLD:
                    continue
                definition = self._definitions.get(def_id)
                if definition is None:
                    continue
                recommendations.append((pct, definition))

        recommendations.sort(key=lambda x: x[0], reverse=True)
        return [defn for _, defn in recommendations[:max_recommendations]]

    def generate_milestone_achievements(
        self,
        player_id: str,
        count: int = 3,
    ) -> List[AchievementDefinition]:
        """Create personalized milestone achievements based on the player's
        current stats and progress.

        Analyzes the player's achievement track record and generates
        milestone challenges appropriate to their current standing.
        """
        stats = self.get_player_stats(player_id)
        generated: List[AchievementDefinition] = []

        with self._lock:
            total_achievements = stats["total_achievements"]
            total_claimed = stats["claimed"]
            total_unlocked = stats["unlocked"]
            total_points = stats["total_points"]

            if total_claimed >= 10:
                next_target = ((total_claimed // 10) + 1) * 10
                name = f"Claim {next_target} Achievements"
                definition = self.create_achievement(
                    name=name,
                    description=f"Claim a total of {next_target} achievement rewards",
                    category=AchievementCategory.MILESTONE,
                    rarity=AchievementRarity.UNCOMMON if next_target < 50 else AchievementRarity.RARE,
                    target_value=float(next_target),
                    reward_exp=next_target * 15,
                    reward_currency=next_target * 8,
                )
                generated.append(definition)

            if total_points >= 100:
                next_point_milestone = ((total_points // 100) + 1) * 100
                name = f"Score: {next_point_milestone} Points"
                rarity = AchievementRarity.COMMON
                if next_point_milestone >= 1000:
                    rarity = AchievementRarity.UNCOMMON
                if next_point_milestone >= 5000:
                    rarity = AchievementRarity.RARE
                if next_point_milestone >= 10000:
                    rarity = AchievementRarity.EPIC
                definition = self.create_achievement(
                    name=name,
                    description=f"Accumulate {next_point_milestone} total achievement points",
                    category=AchievementCategory.MILESTONE,
                    rarity=rarity,
                    target_value=float(next_point_milestone),
                    reward_exp=int(next_point_milestone * 0.8),
                    reward_currency=int(next_point_milestone * 0.4),
                )
                generated.append(definition)

            category_counts = stats.get("by_category", {})
            if category_counts:
                best_category = max(category_counts, key=category_counts.get)
                best_count = category_counts[best_category]
                next_count = best_count + 5
                name = f"{best_category.title()} Expert: {next_count}"
                try:
                    cat_enum = AchievementCategory(best_category)
                except ValueError:
                    cat_enum = AchievementCategory.MILESTONE
                definition = self.create_achievement(
                    name=name,
                    description=f"Unlock {next_count} achievements in the {best_category} category",
                    category=cat_enum,
                    rarity=AchievementRarity.RARE if next_count >= 20 else AchievementRarity.UNCOMMON,
                    target_value=float(next_count),
                    reward_exp=next_count * 20,
                    reward_currency=next_count * 10,
                )
                generated.append(definition)

            remaining = count - len(generated)
            if remaining > 0:
                total_combined = total_unlocked + total_claimed
                next_total = ((total_combined // 5) + 1) * 5
                name = f"Total Completion: {next_total}"
                definition = self.create_achievement(
                    name=name,
                    description=f"Unlock or claim {next_total} achievements in total",
                    category=AchievementCategory.MILESTONE,
                    rarity=AchievementRarity.COMMON,
                    target_value=float(next_total),
                    reward_exp=next_total * 10,
                    reward_currency=next_total * 5,
                )
                generated.append(definition)

        return generated[:count]

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def get_leaderboard(
        self,
        category: Optional[AchievementCategory] = None,
        limit: int = DEFAULT_LEADERBOARD_LIMIT,
    ) -> List[Dict[str, Any]]:
        """Generate a leaderboard of players ranked by achievement points.

        When a category is provided, only achievements within that category
        are counted. Otherwise, all achievements contribute to the score.
        """
        scores: List[Tuple[str, int, int]] = []

        with self._lock:
            for player_id, records in self._player_achievements.items():
                total_points = 0
                total_count = 0
                for def_id, pa in records.items():
                    if pa.status not in (AchievementStatus.UNLOCKED, AchievementStatus.CLAIMED):
                        continue
                    definition = self._definitions.get(def_id)
                    if definition is None:
                        continue
                    if category is not None and definition.category != category:
                        continue
                    total_points += int(definition.target_value * RARITY_MULTIPLIERS.get(definition.rarity, 1.0))
                    total_count += 1
                if total_points > 0:
                    scores.append((player_id, total_points, total_count))

        scores.sort(key=lambda x: x[1], reverse=True)
        leaderboard = []
        for rank, (player_id, points, count) in enumerate(scores[:limit], start=1):
            leaderboard.append({
                "rank": rank,
                "player_id": player_id,
                "points": points,
                "achievement_count": count,
            })
        return leaderboard

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return global engine statistics and health summary."""
        with self._lock:
            total_definitions = len(self._definitions)
            total_players = len(self._player_achievements)

            category_counts: Dict[str, int] = defaultdict(int)
            rarity_counts: Dict[str, int] = defaultdict(int)
            for definition in self._definitions.values():
                category_counts[definition.category.value] += 1
                rarity_counts[definition.rarity.value] += 1

            total_player_achievements = sum(
                len(records) for records in self._player_achievements.values()
            )

            return {
                "total_definitions": total_definitions,
                "total_players": total_players,
                "total_player_achievement_records": total_player_achievements,
                "total_achievements_created": self._total_achievements_created,
                "total_unlocks": self._total_unlocks,
                "total_claimed": self._total_claimed,
                "unlock_order_counter": self._unlock_order_counter,
                "notification_history_size": len(self._notifications),
                "by_category": dict(category_counts),
                "by_rarity": dict(rarity_counts),
            }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------


def get_achievement_system_engine() -> AchievementSystemEngine:
    """Return the singleton AchievementSystemEngine instance."""
    return AchievementSystemEngine.get_instance()