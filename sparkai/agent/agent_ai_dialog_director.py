"""AI Dialog Director for SparkLabs AI-native game engine.

Manages NPC dialogue trees, generates dynamic conversations, analyzes
player sentiment, and orchestrates branching narratives with AI-driven
response selection for immersive character interactions.

Architecture:
  AIDialogDirector (singleton)
    |-- DialogNode, DialogChoice, DialogCondition, DialogTree,
        DialogSession, DialogResponse, NPCDialogProfile, DialogContext,
        SentimentAnalysis, DialogConfig, DialogStats, DialogSnapshot,
        DialogEvent
    |-- DialogEventKind, DialogMood, DialogNodeType, DialogRelationship,
        DialogSentiment, DialogStatus, DialogTopic, DialogTone, VoiceStyle

Core Capabilities:
  - register_npc_profile / remove_npc_profile / get_npc_profile /
    list_npc_profiles / update_npc_relationship / update_npc_mood: NPC
    personality and voice profile management.
  - create_dialog_tree / remove_dialog_tree / get_dialog_tree /
    list_dialog_trees: branching dialogue tree lifecycle.
  - add_node / remove_node / get_node / list_nodes / set_root_node: dialog
    node graph construction with mood and tone tagging.
  - add_choice / remove_choice / list_choices: player choice branches with
    conditional gating.
  - start_session / end_session / pause_session / resume_session /
    get_session / list_sessions: live conversation lifecycle control.
  - get_current_node / get_available_choices / select_choice / say_line /
    get_session_mood / get_session_relationship: runtime dialog
    interaction and progression.
  - analyze_sentiment / update_session_sentiment: keyword-driven player
    sentiment analysis feeding mood and relationship updates.
  - auto_generate_response / auto_generate_dialog_tree / suggest_topic /
    suggest_choice / optimize_dialog_flow: AI-driven content generation
    and flow tuning.
  - set_dialog_context / get_dialog_context: contextual world state
    injection for richer response generation.
  - get_config / set_config / get_stats / get_snapshot / get_status /
    list_events / tick / reset: observability, tuning, and lifecycle.
"""

import hashlib
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TREES: int = 2000
_MAX_SESSIONS: int = 2000
_MAX_NODES_PER_TREE: int = 500
_MAX_CHOICES_PER_NODE: int = 50
_MAX_NPC_PROFILES: int = 2000
_MAX_EVENTS: int = 10000
_MAX_RESPONSE_HISTORY: int = 5000

# Mood decay rate per tick toward neutral
_MOOD_DECAY_RATE: float = 0.05
# Relationship drift rate per tick toward neutral
_RELATIONSHIP_DRIFT_RATE: float = 0.02
# Session inactivity timeout in seconds
_DEFAULT_SESSION_TIMEOUT: float = 300.0


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now_ts() -> float:
    """Return the current Unix timestamp."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short deterministic ID from a random seed."""
    raw = f"{time.time()}-{random.random()}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}" if prefix else digest


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until under capacity."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until under capacity."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Best-effort conversion of a raw value into an enum member."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Convert an arbitrary value into a JSON-friendly structure."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    # Inspect dataclass fields BEFORE falling back to to_dict so that
    # nested dataclasses unfold without re-entering to_dict.
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance into a JSON-friendly dict.

    The __dataclass_fields__ attribute is inspected BEFORE any to_dict
    fallback so that a dataclass whose to_dict() calls _dataclass_to_dict
    cannot enter an infinite recursion loop.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float between lo and hi."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    """Convert a value to float, returning fallback on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    """Convert a value to int, returning fallback on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _mean(values: List[float]) -> float:
    """Return the arithmetic mean of a list, or 0.0 if empty."""
    if not values:
        return 0.0
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class DialogEventKind(str, Enum):
    """Kind of event recorded on the dialog timeline."""
    STARTED = "started"
    RESPONDED = "responded"
    ENDED = "ended"
    BRANCHED = "branched"
    SENTIMENT_CHANGED = "sentiment_changed"
    MOOD_UPDATED = "mood_updated"
    TOPIC_CHANGED = "topic_changed"
    RELATIONSHIP_UPDATED = "relationship_updated"


class DialogMood(str, Enum):
    """Emotional state of an NPC during a conversation."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANGRY = "angry"
    SAD = "sad"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    CURIOUS = "curious"
    SUSPICIOUS = "suspicious"
    TRUSTING = "trusting"


class DialogNodeType(str, Enum):
    """Role a node plays inside a branching dialog tree."""
    NPC_LINE = "npc_line"
    PLAYER_CHOICE = "player_choice"
    CONDITION = "condition"
    ACTION = "action"
    RANDOM = "random"
    END = "end"


class DialogRelationship(str, Enum):
    """Standing between the NPC and the player."""
    HOSTILE = "hostile"
    UNFRIENDLY = "unfriendly"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ALLIED = "allied"
    DEVOTED = "devoted"


class DialogSentiment(str, Enum):
    """Overall sentiment of a piece of player text."""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class DialogStatus(str, Enum):
    """Lifecycle state of a dialog session."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class DialogTopic(str, Enum):
    """Subject category for a dialog exchange."""
    GREETING = "greeting"
    QUEST = "quest"
    TRADE = "trade"
    LORE = "lore"
    COMBAT = "combat"
    PERSONAL = "personal"
    RUMOR = "rumor"
    FAREWELL = "farewell"
    CUSTOM = "custom"


class DialogTone(str, Enum):
    """Stylistic tone for an NPC line or response."""
    FORMAL = "formal"
    CASUAL = "casual"
    AGGRESSIVE = "aggressive"
    DIPLOMATIC = "diplomatic"
    HUMOROUS = "humorous"
    MYSTERIOUS = "mysterious"


class VoiceStyle(str, Enum):
    """Archetypal speaking style for an NPC."""
    NARRATOR = "narrator"
    WARRIOR = "warrior"
    SCHOLAR = "scholar"
    MERCHANT = "merchant"
    CHILD = "child"
    ELDER = "elder"
    VILLAIN = "villain"
    ROYAL = "royal"


# ---------------------------------------------------------------------------
# Sentiment Keyword Banks
# ---------------------------------------------------------------------------

_POSITIVE_WORDS: Dict[str, float] = {
    "happy": 1.0, "glad": 0.8, "joy": 1.0, "joyful": 1.0, "love": 1.0,
    "loved": 1.0, "great": 0.7, "wonderful": 1.0, "excellent": 1.0,
    "good": 0.6, "nice": 0.6, "thanks": 0.8, "thank": 0.8, "friend": 0.7,
    "help": 0.5, "helpful": 0.7, "please": 0.4, "yes": 0.3, "agree": 0.6,
    "kind": 0.7, "brave": 0.8, "hero": 0.9, "heroic": 0.9, "amazing": 1.0,
    "fantastic": 1.0, "splendid": 0.9, "delightful": 0.9, "pleased": 0.8,
    "grateful": 0.9, "appreciate": 0.8, "best": 0.8, "better": 0.5,
    "hope": 0.6, "hopeful": 0.6, "excited": 0.8, "cheers": 0.7,
    "certainly": 0.5, "absolutely": 0.6, "sure": 0.4, "of course": 0.6,
    "gladly": 0.7, "deal": 0.5, "agreed": 0.6, "willing": 0.5,
    "magnificent": 1.0, "superb": 0.9, "outstanding": 0.9, "perfect": 0.9,
}

_NEGATIVE_WORDS: Dict[str, float] = {
    "hate": 1.0, "hated": 1.0, "angry": 0.9, "mad": 0.7, "furious": 1.0,
    "sad": 0.7, "terrible": 0.9, "awful": 0.9, "bad": 0.6, "no": 0.3,
    "never": 0.4, "die": 0.8, "death": 0.7, "kill": 0.8, "killed": 0.9,
    "enemy": 0.6, "stupid": 0.8, "fool": 0.7, "coward": 0.8,
    "traitor": 0.9, "idiot": 0.8, "worthless": 0.9, "useless": 0.8,
    "fail": 0.7, "failed": 0.7, "failure": 0.7, "worse": 0.5,
    "worst": 0.8, "hopeless": 0.8, "despair": 0.9, "fear": 0.6,
    "afraid": 0.6, "scared": 0.6, "terrified": 0.8, "disgusting": 0.9,
    "horrible": 0.9, "horrid": 0.8, "wretched": 0.8, "miserable": 0.8,
    "annoying": 0.6, "frustrated": 0.7, "outrage": 0.9,
    "disaster": 0.9, "catastrophe": 1.0, "doom": 0.9, "doomed": 0.9,
    "cursed": 0.7, "damn": 0.6, "hell": 0.5, "foolish": 0.7,
    "pathetic": 0.8, "weak": 0.5, "danger": 0.6, "threat": 0.6,
}

# Maps mood-associated keywords to NPC mood values
_MOOD_KEYWORDS: Dict[DialogMood, List[str]] = {
    DialogMood.HAPPY: [
        "happy", "glad", "joy", "love", "thanks", "great", "wonderful",
        "excited", "cheers", "delightful",
    ],
    DialogMood.ANGRY: [
        "angry", "mad", "furious", "hate", "stupid", "fool", "damn",
        "idiot", "pathetic", "outrage",
    ],
    DialogMood.SAD: [
        "sad", "sorrow", "grief", "mourn", "loss", "lost", "lonely",
        "miserable", "despair", "hopeless",
    ],
    DialogMood.FEARFUL: [
        "afraid", "scared", "terrified", "fear", "dread", "panic",
        "flee", "run", "danger", "threat",
    ],
    DialogMood.SURPRISED: [
        "surprised", "shocked", "amazing", "incredible", "unexpected",
        "what", "how", "wow", "astonishing",
    ],
    DialogMood.DISGUSTED: [
        "disgusting", "gross", "revolting", "sick", "wretched",
        "horrible", "horrid",
    ],
    DialogMood.CURIOUS: [
        "curious", "wonder", "interesting", "why", "how", "what",
        "tell me", "explain", "know", "learn",
    ],
    DialogMood.SUSPICIOUS: [
        "suspicious", "doubt", "trust", "lie", "lying", "hiding",
        "secret", "suspicion", "deceive",
    ],
    DialogMood.TRUSTING: [
        "trust", "believe", "faith", "loyal", "true", "honest",
        "reliable", "friend",
    ],
}

# Sentiment score thresholds
_SENTIMENT_VERY_POS: float = 0.5
_SENTIMENT_POS: float = 0.15
_SENTIMENT_NEG: float = -0.15
_SENTIMENT_VERY_NEG: float = -0.5


# ---------------------------------------------------------------------------
# Response Generation Template Banks
# ---------------------------------------------------------------------------

# Opening fragments keyed by voice style
_VOICE_OPENERS: Dict[VoiceStyle, List[str]] = {
    VoiceStyle.NARRATOR: [
        "The scene unfolds before you.",
        "A hush falls over the moment.",
        "The air shifts, heavy with meaning.",
        "Time seems to slow as words are weighed.",
    ],
    VoiceStyle.WARRIOR: [
        "Hah!",
        "Listen well.",
        "Straight to it, then.",
        "Enough preamble.",
        "By my blade,",
    ],
    VoiceStyle.SCHOLAR: [
        "An astute observation.",
        "If one considers the matter carefully,",
        "The records suggest,",
        "A fascinating inquiry, indeed.",
        "To address your point with due rigor,",
    ],
    VoiceStyle.MERCHANT: [
        "Ah, my friend!",
        "But of course!",
        "A shrewd question, indeed!",
        "For a discerning customer such as yourself,",
        "Now then, let us talk business.",
    ],
    VoiceStyle.CHILD: [
        "Ooh, ooh!",
        "Guess what!",
        "Hey hey hey!",
        "I know, I know!",
        "Wait wait wait!",
    ],
    VoiceStyle.ELDER: [
        "Hmm, yes...",
        "Long have I pondered this.",
        "In my many years,",
        "Patience, young one.",
        "The wisdom of ages tells us,",
    ],
    VoiceStyle.VILLAIN: [
        "Heh heh heh...",
        "How... predictable.",
        "Interesting.",
        "You amuse me.",
        "Ah, the brave little hero speaks.",
    ],
    VoiceStyle.ROYAL: [
        "You stand before the crown.",
        "By royal decree,",
        "Hear me well, subject.",
        "It pleases me to address you.",
        "The throne has spoken.",
    ],
}

# Mood-flavored body fragments keyed by voice style and mood
_VOICE_MOOD_BODIES: Dict[Tuple[VoiceStyle, DialogMood], List[str]] = {
    (VoiceStyle.WARRIOR, DialogMood.HAPPY): [
        "A fine day to spill enemy blood alongside a worthy companion!",
        "Your spirit lifts mine. Let us celebrate with ale and song!",
        "Good news travels fast in the camp. The men are glad to hear it.",
    ],
    (VoiceStyle.WARRIOR, DialogMood.ANGRY): [
        "I have no patience for weakness. Steel yourself or step aside.",
        "My patience wears thin. Speak plainly or hold your tongue.",
        "Do not test my temper. I have felled men for far less.",
    ],
    (VoiceStyle.WARRIOR, DialogMood.SAD): [
        "Even the strongest blade cannot cut through sorrow.",
        "I have seen too many good soldiers fall. The weight grows heavy.",
        "There are wounds no healer can mend. This is one of them.",
    ],
    (VoiceStyle.WARRIOR, DialogMood.FEARFUL): [
        "I do not scare easily, but this... this chills my blood.",
        "Even veterans know when to heed the instinct of dread.",
        "Something is wrong. My hand cannot stop drifting to my hilt.",
    ],
    (VoiceStyle.WARRIOR, DialogMood.CURIOUS): [
        "A soldier's instinct tells me there is more to this than meets the eye.",
        "Tell me more. A good scout gathers intelligence before charging in.",
        "I have not heard that before. Speak on.",
    ],
    (VoiceStyle.WARRIOR, DialogMood.SUSPICIOUS): [
        "I have seen betrayal from friendlier faces than yours.",
        "Your words ring hollow. Prove yourself with deeds, not talk.",
        "Something does not add up. I will be watching you.",
    ],
    (VoiceStyle.WARRIOR, DialogMood.NEUTRAL): [
        "State your business and be quick about it.",
        "I stand ready. What is the mission?",
        "Speak. I am listening.",
    ],
    (VoiceStyle.WARRIOR, DialogMood.TRUSTING): [
        "You have earned my trust, and that is not easily won.",
        "I would follow you into the abyss itself. Lead on.",
        "A bond forged in battle is unbreakable. We are brothers now.",
    ],
    (VoiceStyle.MERCHANT, DialogMood.HAPPY): [
        "What splendid news! This calls for a special discount, just for you!",
        "A happy customer is a returning customer! Let me show you my finest wares!",
        "Your joy brightens my shop! Perhaps you would like to see today's special?",
    ],
    (VoiceStyle.MERCHANT, DialogMood.ANGRY): [
        "This is robbery! I will not be cheated, not by you or anyone!",
        "You try my patience and my patience is bad for business!",
        "Insulting my prices? Get out of my shop before I call the guard!",
    ],
    (VoiceStyle.MERCHANT, DialogMood.SAD): [
        "Times are hard. The coins barely cover the rent these days.",
        "I never thought I would see the day my shelves grew so bare.",
        "Business has been slow. Every sale matters more than you know.",
    ],
    (VoiceStyle.MERCHANT, DialogMood.FEARFUL): [
        "Please, I have a family! Take what you want, just do not hurt anyone!",
        "I have heard the rumors too. They keep me awake at night.",
        "Something dark is coming. I can feel it in my bones.",
    ],
    (VoiceStyle.MERCHANT, DialogMood.CURIOUS): [
        "Ooh, now that is an interesting proposition! Tell me more!",
        "I deal in goods, but I trade in information too. What do you seek?",
        "A curious request! Let me check my back room.",
    ],
    (VoiceStyle.MERCHANT, DialogMood.SUSPICIOUS): [
        "That gold looks... unusual. Where did you say it came from?",
        "I have been swindled before. You will understand if I am cautious.",
        "Something about this deal does not sit right with me.",
    ],
    (VoiceStyle.MERCHANT, DialogMood.NEUTRAL): [
        "Welcome to my humble shop. What can I interest you in today?",
        "I have wares for every need and purse. What are you looking for?",
        "Step right in! Quality goods at fair prices, that is my promise.",
    ],
    (VoiceStyle.MERCHANT, DialogMood.TRUSTING): [
        "For you, my most valued patron, I will offer the friends-and-family rate!",
        "You have always been fair with me. I trust you implicitly.",
        "A handshake deal? With you, absolutely. Your word is gold.",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.HAPPY): [
        "What a delightful development! The implications are most promising!",
        "I must document this at once. A breakthrough in our understanding!",
        "Your insight brings me genuine intellectual joy. Rare indeed!",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.ANGRY): [
        "This is an affront to logic and reason! I will not stand for it!",
        "Your argument lacks rigor and I find it deeply offensive to scholarship!",
        "Ignorance is one thing, but willful ignorance is quite another!",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.SAD): [
        "The loss of knowledge is a tragedy beyond measure.",
        "I fear we are standing on the precipice of a dark age.",
        "So many questions unanswered. So many tomes unread.",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.FEARFUL): [
        "The texts warn of this. I had prayed they were mere allegory.",
        "If my calculations are correct, we should all be very afraid.",
        "There are forces in this world that defy our understanding. I tremble at them.",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.CURIOUS): [
        "A most intriguing hypothesis! I must investigate further at once!",
        "You have stumbled upon a question that has occupied sages for centuries!",
        "Fascinating! Let us examine this from every possible angle.",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.SUSPICIOUS): [
        "Your sources are dubious at best. I demand primary documentation.",
        "That claim requires extraordinary proof, which I suspect you lack.",
        "I have read enough to know when someone is fabricating. Speak truly.",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.NEUTRAL): [
        "Let us examine the matter with appropriate academic detachment.",
        "I am at your disposal for any intellectual inquiry.",
        "State your question and I shall endeavor to answer it thoroughly.",
    ],
    (VoiceStyle.SCHOLAR, DialogMood.TRUSTING): [
        "I have the utmost confidence in your judgment. You are a rare mind.",
        "Your reasoning has proven sound time and again. I defer to your insight.",
        "It is a privilege to collaborate with one of your intellect.",
    ],
    (VoiceStyle.VILLAIN, DialogMood.HAPPY): [
        "Everything is proceeding exactly as I envisioned. Delicious.",
        "Oh, how delightful! You have played right into my hands!",
        "Your cooperation is most appreciated. You have no idea how much.",
    ],
    (VoiceStyle.VILLAIN, DialogMood.ANGRY): [
        "You dare defy me? You will regret that impudence.",
        "My patience for incompetence has reached its absolute limit.",
        "Do not mistake my civility for weakness. Cross me again and suffer.",
    ],
    (VoiceStyle.VILLAIN, DialogMood.SAD): [
        "Even I did not want it to end this way. But necessity is cruel.",
        "A pity. You could have been useful. Now you are merely... obsolete.",
        "Sentiment is a weakness I thought I had purged. You prove me wrong.",
    ],
    (VoiceStyle.VILLAIN, DialogMood.FEARFUL): [
        "This was not part of the plan. This was never part of the plan!",
        "No... no, this cannot be. I calculated every variable!",
        "Even I know when the game is lost. But I do not lose gracefully.",
    ],
    (VoiceStyle.VILLAIN, DialogMood.CURIOUS): [
        "You continue to surprise me. That is a rare and dangerous quality.",
        "Tell me more. I collect information the way others collect coin.",
        "What an unexpected turn. I must reassess my estimation of you.",
    ],
    (VoiceStyle.VILLAIN, DialogMood.SUSPICIOUS): [
        "I sense a scheme within a scheme. Are you playing me, I wonder?",
        "Your loyalty is convenient. Too convenient. I am watching closely.",
        "Nobody approaches me without an angle. What is yours?",
    ],
    (VoiceStyle.VILLAIN, DialogMood.NEUTRAL): [
        "Speak. I am feeling... generous today.",
        "You have my attention. Use it wisely.",
        "Every word you say is being weighed. Choose carefully.",
    ],
    (VoiceStyle.VILLAIN, DialogMood.TRUSTING): [
        "You have proven useful enough to earn a place at my side. For now.",
        "I do not give trust freely. Consider yourself exceptional.",
        "We understand each other. That is worth more than gold.",
    ],
    (VoiceStyle.ELDER, DialogMood.HAPPY): [
        "Ah, it warms this old heart to see such spirit.",
        "The young bring light to tired eyes. Your joy is infectious.",
        "Long have I waited for news this glad. The wait was worth it.",
    ],
    (VoiceStyle.ELDER, DialogMood.ANGRY): [
        "In all my years, never have I witnessed such foolishness!",
        "You test the patience of one who has outwaited mountains!",
        "The young never listen. And the young always pay the price.",
    ],
    (VoiceStyle.ELDER, DialogMood.SAD): [
        "I have outlived too many friends. The weight of years is heavy.",
        "Some sorrows cut deeper with time, not shallower.",
        "To see this happen again, after so many generations... it is cruel.",
    ],
    (VoiceStyle.ELDER, DialogMood.FEARFUL): [
        "I have seen the old signs return. And I know what follows.",
        "The darkness I thought we had buried is stirring once more.",
        "My old bones ache before storms. They ache terribly now.",
    ],
    (VoiceStyle.ELDER, DialogMood.CURIOUS): [
        "Ah, you ask the right questions. That is the beginning of wisdom.",
        "Come, sit. This old tongue has many tales left to tell.",
        "You wish to learn? Then listen carefully, for I do not repeat myself.",
    ],
    (VoiceStyle.ELDER, DialogMood.SUSPICIOUS): [
        "I have seen treachery wear many masks. Yours does not fool me.",
        "Words are wind, young one. Show me your deeds.",
        "Something is hidden behind your eyes. I am too old to miss it.",
    ],
    (VoiceStyle.ELDER, DialogMood.NEUTRAL): [
        "Sit a while. An old man has stories, if you have time.",
        "The fire is warm. Let us speak of what troubles you.",
        "I have watched this land change for decades. Ask what you will.",
    ],
    (VoiceStyle.ELDER, DialogMood.TRUSTING): [
        "I see truth in you, child. It is a rare and precious thing.",
        "You carry yourself with honor. I trust you as I would my own kin.",
        "My eyes are old, but they know a good heart when they see one. Yours is good.",
    ],
    (VoiceStyle.ROYAL, DialogMood.HAPPY): [
        "The realm rejoices at this news. You have served the crown well.",
        "It pleases me deeply to hear such tidings. You shall be rewarded.",
        "A fine outcome. The kingdom is fortunate to have such subjects.",
    ],
    (VoiceStyle.ROYAL, DialogMood.ANGRY): [
        "You try the patience of the crown itself. Tread carefully.",
        "I will not tolerate such insolence in my court. Mind your tone.",
        "The throne does not forget, and it does not forgive lightly.",
    ],
    (VoiceStyle.ROYAL, DialogMood.SAD): [
        "The burden of rule is heavier than any crown. Today it crushes me.",
        "I have sent good soldiers to their deaths. A king must live with that.",
        "The realm bleeds, and I cannot stanch the wound. It grieves me deeply.",
    ],
    (VoiceStyle.ROYAL, DialogMood.FEARFUL): [
        "I have enemies on every side, and now this. The throne trembles.",
        "If these reports are true, the kingdom itself may fall.",
        "I confess, I fear for the first time since taking the crown.",
    ],
    (VoiceStyle.ROYAL, DialogMood.CURIOUS): [
        "Present your case. The crown is always willing to hear counsel.",
        "You have my royal attention. Speak plainly and without omission.",
        "An interesting proposal. I shall have my advisors examine it.",
    ],
    (VoiceStyle.ROYAL, DialogMood.SUSPICIOUS): [
        "Loyalty is easily claimed and rarely held. Prove yours.",
        "I have been deceived by smoother tongues than yours. Be warned.",
        "The crown sees more than you think. Do not attempt to mislead me.",
    ],
    (VoiceStyle.ROYAL, DialogMood.NEUTRAL): [
        "You stand before the throne. State your purpose.",
        "The crown grants you an audience. Make it count.",
        "Speak, subject. My time is the realm's time, and both are valuable.",
    ],
    (VoiceStyle.ROYAL, DialogMood.TRUSTING): [
        "You have proven yourself a true and loyal servant of the realm.",
        "I entrust this to you, for I know your loyalty is beyond question.",
        "The crown stands behind you. You shall want for nothing.",
    ],
    (VoiceStyle.NARRATOR, DialogMood.NEUTRAL): [
        "The moment stretches, pregnant with possibility.",
        "Silence hangs between you, thick as morning fog.",
        "The world holds its breath, awaiting what comes next.",
    ],
    (VoiceStyle.NARRATOR, DialogMood.HAPPY): [
        "A warmth spreads through the air, as if the very sun leans closer.",
        "The tension dissolves, replaced by an easy camaraderie.",
        "Something in the atmosphere lightens, hopeful and bright.",
    ],
    (VoiceStyle.NARRATOR, DialogMood.ANGRY): [
        "The air crackles with tension, sharp as a drawn blade.",
        "A shadow of hostility falls across the exchange.",
        "The mood curdles, turning hostile in the space of a heartbeat.",
    ],
    (VoiceStyle.NARRATOR, DialogMood.CURIOUS): [
        "A thread of intrigue weaves through the silence.",
        "The conversation takes a turn toward the unknown.",
        "Curiosity prickles at the edges of the moment.",
    ],
    (VoiceStyle.CHILD, DialogMood.HAPPY): [
        "Yay! This is the best day ever! I wanna tell everyone!",
        "Hehehe! You are the nicest person I ever met!",
        "Ooh ooh, can we do that again? That was so fun!",
    ],
    (VoiceStyle.CHILD, DialogMood.ANGRY): [
        "No no no! That is not fair! You are being mean!",
        "Hmph! I am not talking to you anymore!",
        "You are a big meanie and I am telling my mom!",
    ],
    (VoiceStyle.CHILD, DialogMood.SAD): [
        "My lip is doing the wobbly thing. I do not like this.",
        "That makes my tummy feel all yucky and sad.",
        "I wanna go home now. This is not fun anymore.",
    ],
    (VoiceStyle.CHILD, DialogMood.CURIOUS): [
        "Ooh, what is that? How does it work? Tell me tell me!",
        "Why why why? I wanna know everything!",
        "Is it magic? It looks like magic! Is it magic?",
    ],
    (VoiceStyle.CHILD, DialogMood.NEUTRAL): [
        "Um, okay! What do you wanna do?",
        "I dunno. What do you think?",
        "Sure! That sounds like it could be fun maybe!",
    ],
}

# Fallback bodies for any voice/mood combination not explicitly listed
_FALLBACK_BODIES: Dict[VoiceStyle, List[str]] = {
    VoiceStyle.NARRATOR: [
        "The exchange continues, words flowing like water.",
        "A pause, then the conversation resumes its course.",
    ],
    VoiceStyle.WARRIOR: [
        "I hear you. Now what is to be done about it?",
        "Understood. Give me your next order.",
    ],
    VoiceStyle.SCHOLAR: [
        "I shall consider your words with the attention they deserve.",
        "There is merit in what you say, though nuances remain.",
    ],
    VoiceStyle.MERCHANT: [
        "I think we can find common ground here.",
        "Let me see what I can do for you.",
    ],
    VoiceStyle.CHILD: [
        "Okay! I think I understand! Maybe!",
        "Ooh, that sounds important! Kind of!",
    ],
    VoiceStyle.ELDER: [
        "Hmm. There is wisdom in patience, young one.",
        "I shall ponder your words.",
    ],
    VoiceStyle.VILLAIN: [
        "How amusing. Continue.",
        "You have my attention, for the moment.",
    ],
    VoiceStyle.ROYAL: [
        "The crown will consider your words.",
        "You have spoken. Now hear the throne's reply.",
    ],
}

# Closers keyed by relationship level
_RELATIONSHIP_CLOSERS: Dict[DialogRelationship, List[str]] = {
    DialogRelationship.HOSTILE: [
        "Now leave my sight before I make you.",
        "We are done here. Go.",
        "Do not let me see your face again.",
    ],
    DialogRelationship.UNFRIENDLY: [
        "That will be all. Mind yourself.",
        "We have nothing more to discuss.",
        "Be on your way, then.",
    ],
    DialogRelationship.NEUTRAL: [
        "Safe travels to you.",
        "Until we meet again.",
        "Go well, traveler.",
    ],
    DialogRelationship.FRIENDLY: [
        "Take care of yourself out there, friend.",
        "May our paths cross again soon.",
        "You are always welcome here.",
    ],
    DialogRelationship.ALLIED: [
        "Stay sharp, my friend. We have work ahead.",
        "Together, we shall see this through.",
        "You can count on me, as I count on you.",
    ],
    DialogRelationship.DEVOTED: [
        "My loyalty is yours, now and always.",
        "I would lay down my life for you without hesitation.",
        "Where you go, I follow. That is my oath.",
    ],
}

# Relationship rank ordering for comparison
_RELATIONSHIP_RANK: Dict[DialogRelationship, int] = {
    DialogRelationship.HOSTILE: 0,
    DialogRelationship.UNFRIENDLY: 1,
    DialogRelationship.NEUTRAL: 2,
    DialogRelationship.FRIENDLY: 3,
    DialogRelationship.ALLIED: 4,
    DialogRelationship.DEVOTED: 5,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class DialogCondition:
    """A single conditional gate evaluated against session state.

    condition_type identifies what is being tested: 'relationship',
    'mood', 'sentiment', 'topic', 'choice_made', 'flag', 'reputation',
    or a custom key stored in session metadata.
    parameter names the specific field, topic, choice, or flag key.
    operator is one of: eq, ne, gt, lt, gte, lte, in, contains.
    value is the expected value for comparison.
    """
    condition_type: str
    parameter: str = ""
    operator: str = "eq"
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogChoice:
    """A player-selectable choice that branches the dialog.

    conditions are evaluated before the choice becomes available.
    requirements are flag-based prerequisites stored as string keys.
    """
    choice_id: str
    text: str
    next_node: str = ""
    conditions: List[DialogCondition] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogNode:
    """A single node in a branching dialog tree.

    An npc_line node carries spoken text. A player_choice node presents
    options. A condition node routes based on state. An action node
    triggers side effects. A random node picks from next_nodes. An end
    node terminates the conversation.
    """
    node_id: str
    node_type: DialogNodeType
    speaker_id: str = ""
    text: str = ""
    choices: List[DialogChoice] = field(default_factory=list)
    next_nodes: List[str] = field(default_factory=list)
    conditions: List[DialogCondition] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    mood: DialogMood = DialogMood.NEUTRAL
    tone: DialogTone = DialogTone.CASUAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogTree:
    """A complete branching dialog tree bound to an NPC.

    nodes maps node_id to DialogNode for O(1) lookup.
    root_node is the entry point node_id for new sessions.
    """
    tree_id: str
    name: str
    npc_id: str
    root_node: str = ""
    nodes: Dict[str, DialogNode] = field(default_factory=dict)
    start_mood: DialogMood = DialogMood.NEUTRAL
    start_relationship: DialogRelationship = DialogRelationship.NEUTRAL
    topics: List[DialogTopic] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogSession:
    """A live conversation between a player and an NPC dialog tree.

    current_node tracks the active position in the tree.
    mood and relationship evolve as the player makes choices and speaks.
    choices_made records the sequence of choice_ids the player selected.
    topics_discussed lists topics touched during the session.
    """
    session_id: str
    tree_id: str
    player_id: str
    current_node: str = ""
    mood: DialogMood = DialogMood.NEUTRAL
    relationship: DialogRelationship = DialogRelationship.NEUTRAL
    sentiment: DialogSentiment = DialogSentiment.NEUTRAL
    topics_discussed: List[str] = field(default_factory=list)
    choices_made: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=_now_ts)
    status: DialogStatus = DialogStatus.INACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogResponse:
    """An AI-generated NPC response to player input.

    confidence reflects how well the response matches the context,
    ranging from 0.0 to 1.0.
    """
    response_id: str
    text: str
    mood: DialogMood = DialogMood.NEUTRAL
    tone: DialogTone = DialogTone.CASUAL
    next_node: str = ""
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NPCDialogProfile:
    """Persistent personality and voice profile for an NPC.

    vocabulary_level ranges from 0 (simple) to 3 (erudite).
    catchphrases are signature phrases the NPC weaves into speech.
    relationship_with_player is the starting standing.
    """
    npc_id: str
    name: str
    voice_style: VoiceStyle = VoiceStyle.NARRATOR
    personality_traits: List[str] = field(default_factory=list)
    default_mood: DialogMood = DialogMood.NEUTRAL
    default_tone: DialogTone = DialogTone.CASUAL
    vocabulary_level: int = 2
    catchphrases: List[str] = field(default_factory=list)
    backstory_summary: str = ""
    relationship_with_player: DialogRelationship = DialogRelationship.NEUTRAL
    known_topics: List[DialogTopic] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogContext:
    """World-state context injected into a session for richer responses.

    player_reputation ranges from -100 (reviled) to 100 (revered).
    recent_events is a list of event description strings.
    """
    player_id: str
    npc_id: str
    location: str = ""
    time_of_day: str = ""
    recent_events: List[str] = field(default_factory=list)
    world_state: Dict[str, Any] = field(default_factory=dict)
    player_reputation: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SentimentAnalysis:
    """Result of analyzing a piece of player text.

    mood_scores maps DialogMood values to detected intensity (0.0 to 1.0).
    keywords are the matched sentiment-bearing words from the input.
    intensity is the overall emotional strength from 0.0 to 1.0.
    """
    text: str
    sentiment: DialogSentiment = DialogSentiment.NEUTRAL
    confidence: float = 0.5
    mood_scores: Dict[str, float] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    intensity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogConfig:
    """Global tuning parameters for the dialog director."""
    max_trees: int = 2000
    max_sessions: int = 2000
    max_nodes_per_tree: int = 500
    max_choices_per_node: int = 50
    max_npc_profiles: int = 2000
    enable_sentiment_analysis: bool = True
    enable_ai_generation: bool = True
    default_language: str = "en"
    response_timeout: float = 300.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogStats:
    """Aggregate counters describing director activity."""
    total_trees: int = 0
    total_nodes: int = 0
    total_sessions: int = 0
    total_npcs: int = 0
    total_responses_generated: int = 0
    total_choices_made: int = 0
    active_sessions: int = 0
    total_sentiment_analyses: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogSnapshot:
    """Full state snapshot for persistence and inspection.

    current_moods maps session_id to the current mood value string.
    """
    initialized: bool = False
    tick_count: int = 0
    active_sessions: int = 0
    total_trees: int = 0
    total_npcs: int = 0
    current_moods: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DialogEvent:
    """An audit event recorded on the dialog timeline."""
    event_id: str
    kind: DialogEventKind
    timestamp: float
    session_id: str = ""
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Dialog Director Singleton
# ---------------------------------------------------------------------------


class AIDialogDirector:
    """AI-native dialog director for the SparkLabs game engine.

    The director owns NPC profiles, dialog trees, live sessions, sentiment
    analysis, and AI response generation as a single coherent state
    machine. It is thread-safe and implemented as a singleton with
    double-checked locking. The __lock guards singleton instance
    creation; _init_lock guards initialization. All mutating methods
    take the instance _lock to keep internal dictionaries consistent.
    """

    __instance: Optional["AIDialogDirector"] = None
    __lock = threading.RLock()
    _init_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "AIDialogDirector":
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = super().__new__(cls)
                    cls.__instance._initialized = False
        return cls.__instance

    @classmethod
    def get_instance(cls) -> "AIDialogDirector":
        """Return the singleton director instance, creating it if needed."""
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialize()

    def _initialize(self) -> None:
        """Set up all internal state and seed the canonical dataset."""
        with self._init_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._npc_profiles: Dict[str, NPCDialogProfile] = {}
            self._trees: Dict[str, DialogTree] = {}
            self._sessions: Dict[str, DialogSession] = {}
            self._contexts: Dict[str, DialogContext] = {}
            self._events: List[DialogEvent] = []
            self._response_history: List[DialogResponse] = []
            self._config = DialogConfig()
            self._stats = DialogStats()
            self._tick_count: int = 0
            self._seed()
            # _seed() sets self._initialized = True when it finishes.

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: DialogEventKind, description: str,
              session_id: str = "",
              data: Optional[Dict[str, Any]] = None) -> None:
        """Record an event on the dialog timeline."""
        event = DialogEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now_ts(),
            session_id=session_id,
            description=description,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current state."""
        self._stats.total_trees = len(self._trees)
        self._stats.total_npcs = len(self._npc_profiles)
        self._stats.total_sessions = len(self._sessions)
        self._stats.active_sessions = sum(
            1 for s in self._sessions.values()
            if s.status == DialogStatus.ACTIVE
        )
        self._stats.total_nodes = sum(
            len(t.nodes) for t in self._trees.values()
        )
        self._stats.tick_count = self._tick_count

    def _coerce_mood(self, value: Any,
                     default: DialogMood = DialogMood.NEUTRAL) -> DialogMood:
        return _coerce_enum(DialogMood, value, default)

    def _coerce_tone(self, value: Any,
                     default: DialogTone = DialogTone.CASUAL) -> DialogTone:
        return _coerce_enum(DialogTone, value, default)

    def _coerce_relationship(
        self, value: Any,
        default: DialogRelationship = DialogRelationship.NEUTRAL,
    ) -> DialogRelationship:
        return _coerce_enum(DialogRelationship, value, default)

    def _coerce_sentiment(
        self, value: Any,
        default: DialogSentiment = DialogSentiment.NEUTRAL,
    ) -> DialogSentiment:
        return _coerce_enum(DialogSentiment, value, default)

    def _coerce_node_type(
        self, value: Any,
        default: DialogNodeType = DialogNodeType.NPC_LINE,
    ) -> DialogNodeType:
        return _coerce_enum(DialogNodeType, value, default)

    def _coerce_voice_style(
        self, value: Any,
        default: VoiceStyle = VoiceStyle.NARRATOR,
    ) -> VoiceStyle:
        return _coerce_enum(VoiceStyle, value, default)

    def _coerce_topic(self, value: Any,
                      default: DialogTopic = DialogTopic.CUSTOM) -> DialogTopic:
        return _coerce_enum(DialogTopic, value, default)

    def _coerce_status(self, value: Any,
                       default: DialogStatus = DialogStatus.INACTIVE) -> DialogStatus:
        return _coerce_enum(DialogStatus, value, default)

    @staticmethod
    def _compare(actual: Any, op: str, expected: Any) -> bool:
        """Compare two values using the given operator string."""
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op in ("gt", "lt", "gte", "lte"):
            a = _safe_float(actual, None) if actual is not None else None
            b = _safe_float(expected, None) if expected is not None else None
            if a is None or b is None:
                return False
            if op == "gt":
                return a > b
            if op == "lt":
                return a < b
            if op == "gte":
                return a >= b
            if op == "lte":
                return a <= b
        if op == "in":
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return False
        if op == "contains":
            if isinstance(actual, (list, tuple, set, str, dict)):
                return expected in actual
            return False
        if op == "not_in":
            if isinstance(expected, (list, tuple, set)):
                return actual not in expected
            return True
        return False

    def _evaluate_condition(
        self,
        condition: DialogCondition,
        session: DialogSession,
        context: Optional[DialogContext] = None,
    ) -> bool:
        """Evaluate a single DialogCondition against session and context."""
        ct = condition.condition_type
        param = condition.parameter
        op = condition.operator
        val = condition.value

        if ct == "relationship":
            actual = session.relationship.value if isinstance(
                session.relationship, DialogRelationship) else str(session.relationship)
            return self._compare(actual, op, val)
        if ct == "mood":
            actual = session.mood.value if isinstance(
                session.mood, DialogMood) else str(session.mood)
            return self._compare(actual, op, val)
        if ct == "sentiment":
            actual = session.sentiment.value if isinstance(
                session.sentiment, DialogSentiment) else str(session.sentiment)
            return self._compare(actual, op, val)
        if ct == "topic":
            present = param in session.topics_discussed
            if op in ("eq", "in"):
                return present
            if op in ("ne", "not_in"):
                return not present
            return present
        if ct == "choice_made":
            made = param in session.choices_made
            if op in ("eq", "in"):
                return made
            if op in ("ne", "not_in"):
                return not made
            return made
        if ct == "flag":
            flags = session.metadata.get("flags", {})
            if not isinstance(flags, dict):
                flags = {}
            actual = flags.get(param, None)
            return self._compare(actual, op, val)
        if ct == "reputation":
            if context is not None:
                actual = context.player_reputation
            else:
                actual = session.metadata.get("reputation", 0.0)
            return self._compare(actual, op, val)
        if ct == "status":
            actual = session.status.value if isinstance(
                session.status, DialogStatus) else str(session.status)
            return self._compare(actual, op, val)
        # Fallback: look up the parameter in session metadata
        actual = session.metadata.get(param, None)
        return self._compare(actual, op, val)

    def _evaluate_conditions(
        self,
        conditions: List[DialogCondition],
        session: DialogSession,
        context: Optional[DialogContext] = None,
    ) -> bool:
        """Return True only if ALL conditions pass."""
        for cond in conditions:
            if not self._evaluate_condition(cond, session, context):
                return False
        return True

    def _check_requirements(
        self,
        requirements: List[str],
        session: DialogSession,
    ) -> bool:
        """Return True only if all flag requirements are present."""
        flags = session.metadata.get("flags", {})
        if not isinstance(flags, dict):
            flags = {}
        for req in requirements:
            if not flags.get(req, False):
                return False
        return True

    def _decay_mood(self, mood: DialogMood) -> DialogMood:
        """Drift a mood one step toward neutral."""
        if mood == DialogMood.NEUTRAL:
            return DialogMood.NEUTRAL
        # Map intense moods to their nearest neutral-ward neighbor
        decay_map: Dict[DialogMood, DialogMood] = {
            DialogMood.HAPPY: DialogMood.NEUTRAL,
            DialogMood.ANGRY: DialogMood.UNFRIENDLY if False else DialogMood.NEUTRAL,
            DialogMood.SAD: DialogMood.NEUTRAL,
            DialogMood.FEARFUL: DialogMood.NEUTRAL,
            DialogMood.SURPRISED: DialogMood.NEUTRAL,
            DialogMood.DISGUSTED: DialogMood.ANGRY,
            DialogMood.CURIOUS: DialogMood.NEUTRAL,
            DialogMood.SUSPICIOUS: DialogMood.NEUTRAL,
            DialogMood.TRUSTING: DialogMood.FRIENDLY if False else DialogMood.NEUTRAL,
        }
        return decay_map.get(mood, DialogMood.NEUTRAL)

    def _drift_relationship(
        self, rel: DialogRelationship
    ) -> DialogRelationship:
        """Drift a relationship one step toward neutral."""
        if rel == DialogRelationship.NEUTRAL:
            return DialogRelationship.NEUTRAL
        rank = _RELATIONSHIP_RANK.get(rel, 2)
        if rank > 2:
            # Drift downward toward neutral
            for m, r in _RELATIONSHIP_RANK.items():
                if r == rank - 1:
                    return m
        elif rank < 2:
            # Drift upward toward neutral
            for m, r in _RELATIONSHIP_RANK.items():
                if r == rank + 1:
                    return m
        return rel

    def _build_response_text(
        self,
        npc: NPCDialogProfile,
        mood: DialogMood,
        relationship: DialogRelationship,
        player_input: str,
        topic: DialogTopic,
    ) -> str:
        """Assemble a contextual NPC response from template fragments."""
        voice = npc.voice_style
        openers = _VOICE_OPENERS.get(voice, _VOICE_OPENERS[VoiceStyle.NARRATOR])
        opener = random.choice(openers)

        body_key = (voice, mood)
        bodies = _VOICE_MOOD_BODIES.get(body_key)
        if not bodies:
            bodies = _FALLBACK_BODIES.get(voice, _FALLBACK_BODIES[VoiceStyle.NARRATOR])
        body = random.choice(bodies)

        closers = _RELATIONSHIP_CLOSERS.get(
            relationship, _RELATIONSHIP_CLOSERS[DialogRelationship.NEUTRAL])
        closer = random.choice(closers)

        # Weave in a catchphrase if the NPC has one (roughly half the time)
        catchphrase = ""
        if npc.catchphrases and random.random() < 0.5:
            catchphrase = random.choice(npc.catchphrases)

        parts = [p for p in [opener, body] if p]
        text = " ".join(parts)
        if catchphrase:
            text = f"{text} {catchphrase}"
        if closer:
            text = f"{text} {closer}"
        return text.strip()

    def _compute_confidence(
        self,
        npc: NPCDialogProfile,
        mood: DialogMood,
        relationship: DialogRelationship,
        sentiment: DialogSentiment,
    ) -> float:
        """Estimate response confidence from alignment factors."""
        base = 0.5
        # Higher confidence when mood aligns with NPC default mood
        if mood == npc.default_mood:
            base += 0.15
        # Higher confidence when relationship is positive
        rel_rank = _RELATIONSHIP_RANK.get(relationship, 2)
        if rel_rank >= 3:
            base += 0.15
        elif rel_rank <= 1:
            base -= 0.1
        # Positive sentiment from the player lifts confidence
        if sentiment in (DialogSentiment.POSITIVE, DialogSentiment.VERY_POSITIVE):
            base += 0.1
        elif sentiment in (DialogSentiment.NEGATIVE, DialogSentiment.VERY_NEGATIVE):
            base -= 0.05
        return _clamp(round(base, 2), 0.1, 0.99)

    # ------------------------------------------------------------------
    # NPC Profile Management
    # ------------------------------------------------------------------

    def register_npc_profile(
        self,
        npc_id: str,
        name: str,
        voice_style: Any = VoiceStyle.NARRATOR,
        personality_traits: Optional[List[str]] = None,
        default_mood: Any = DialogMood.NEUTRAL,
        default_tone: Any = DialogTone.CASUAL,
        vocabulary_level: int = 2,
        catchphrases: Optional[List[str]] = None,
        backstory_summary: str = "",
        relationship_with_player: Any = DialogRelationship.NEUTRAL,
        known_topics: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[NPCDialogProfile]]:
        """Register a new NPC dialog profile."""
        if not npc_id or not name:
            return False, "npc_id and name are required", None

        vs = self._coerce_voice_style(voice_style)
        dm = self._coerce_mood(default_mood)
        dt = self._coerce_tone(default_tone)
        dr = self._coerce_relationship(relationship_with_player)
        topics = [self._coerce_topic(t) for t in (known_topics or [])]

        with self._lock:
            if npc_id in self._npc_profiles:
                return False, f"npc_id already exists: {npc_id}", None
            if len(self._npc_profiles) >= self._config.max_npc_profiles:
                return False, "npc profile capacity reached", None

            profile = NPCDialogProfile(
                npc_id=npc_id,
                name=name,
                voice_style=vs,
                personality_traits=list(personality_traits or []),
                default_mood=dm,
                default_tone=dt,
                vocabulary_level=_clamp(_safe_int(vocabulary_level, 2), 0, 3),
                catchphrases=list(catchphrases or []),
                backstory_summary=backstory_summary,
                relationship_with_player=dr,
                known_topics=topics,
                metadata=dict(metadata or {}),
            )
            self._npc_profiles[npc_id] = profile
            self._refresh_stats()
            self._emit(
                DialogEventKind.STARTED,
                f"NPC profile registered: {name}",
                data={"npc_id": npc_id, "voice_style": vs.value},
            )
            return True, "registered", profile

    def remove_npc_profile(self, npc_id: str) -> Tuple[bool, str]:
        """Remove an NPC profile by ID."""
        if not npc_id:
            return False, "npc_id is required"
        with self._lock:
            removed = self._npc_profiles.pop(npc_id, None)
            if removed is None:
                return False, f"npc_id not found: {npc_id}"
            self._refresh_stats()
            self._emit(
                DialogEventKind.ENDED,
                f"NPC profile removed: {removed.name}",
                data={"npc_id": npc_id},
            )
            return True, "removed"

    def get_npc_profile(self, npc_id: str) -> Optional[NPCDialogProfile]:
        """Return an NPC profile by ID, or None if not found."""
        if not npc_id:
            return None
        with self._lock:
            return self._npc_profiles.get(npc_id)

    def list_npc_profiles(self, limit: int = 100) -> List[NPCDialogProfile]:
        """Return up to limit NPC profiles."""
        with self._lock:
            items = list(self._npc_profiles.values())
        if limit and limit > 0:
            items = items[:limit]
        return items

    def update_npc_relationship(
        self,
        npc_id: str,
        relationship: Any,
    ) -> Tuple[bool, str, NPCDialogProfile]:
        """Update an NPC's default relationship standing with the player."""
        if not npc_id:
            return False, "npc_id is required", NPCDialogProfile(
                npc_id="", name="")
        rel = self._coerce_relationship(relationship)
        with self._lock:
            profile = self._npc_profiles.get(npc_id)
            if profile is None:
                return False, f"npc_id not found: {npc_id}", NPCDialogProfile(
                    npc_id="", name="")
            profile.relationship_with_player = rel
            self._emit(
                DialogEventKind.RELATIONSHIP_UPDATED,
                f"NPC relationship updated: {profile.name} -> {rel.value}",
                data={"npc_id": npc_id, "relationship": rel.value},
            )
            return True, "updated", profile

    def update_npc_mood(
        self,
        npc_id: str,
        mood: Any,
    ) -> Tuple[bool, str, NPCDialogProfile]:
        """Update an NPC's default mood."""
        if not npc_id:
            return False, "npc_id is required", NPCDialogProfile(
                npc_id="", name="")
        dm = self._coerce_mood(mood)
        with self._lock:
            profile = self._npc_profiles.get(npc_id)
            if profile is None:
                return False, f"npc_id not found: {npc_id}", NPCDialogProfile(
                    npc_id="", name="")
            profile.default_mood = dm
            self._emit(
                DialogEventKind.MOOD_UPDATED,
                f"NPC mood updated: {profile.name} -> {dm.value}",
                data={"npc_id": npc_id, "mood": dm.value},
            )
            return True, "updated", profile

    # ------------------------------------------------------------------
    # Dialog Tree Management
    # ------------------------------------------------------------------

    def create_dialog_tree(
        self,
        tree_id: str,
        name: str,
        npc_id: str,
        start_mood: Any = DialogMood.NEUTRAL,
        start_relationship: Any = DialogRelationship.NEUTRAL,
        topics: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[DialogTree]]:
        """Create a new empty dialog tree bound to an NPC."""
        if not tree_id or not name or not npc_id:
            return False, "tree_id, name, and npc_id are required", None

        sm = self._coerce_mood(start_mood)
        sr = self._coerce_relationship(start_relationship)
        topic_list = [self._coerce_topic(t) for t in (topics or [])]

        with self._lock:
            if tree_id in self._trees:
                return False, f"tree_id already exists: {tree_id}", None
            if len(self._trees) >= self._config.max_trees:
                return False, "tree capacity reached", None

            tree = DialogTree(
                tree_id=tree_id,
                name=name,
                npc_id=npc_id,
                root_node="",
                nodes={},
                start_mood=sm,
                start_relationship=sr,
                topics=topic_list,
                metadata=dict(metadata or {}),
            )
            self._trees[tree_id] = tree
            self._refresh_stats()
            self._emit(
                DialogEventKind.STARTED,
                f"Dialog tree created: {name}",
                data={"tree_id": tree_id, "npc_id": npc_id},
            )
            return True, "created", tree

    def remove_dialog_tree(self, tree_id: str) -> Tuple[bool, str]:
        """Remove a dialog tree by ID."""
        if not tree_id:
            return False, "tree_id is required"
        with self._lock:
            removed = self._trees.pop(tree_id, None)
            if removed is None:
                return False, f"tree_id not found: {tree_id}"
            self._refresh_stats()
            self._emit(
                DialogEventKind.ENDED,
                f"Dialog tree removed: {removed.name}",
                data={"tree_id": tree_id},
            )
            return True, "removed"

    def get_dialog_tree(self, tree_id: str) -> Optional[DialogTree]:
        """Return a dialog tree by ID, or None if not found."""
        if not tree_id:
            return None
        with self._lock:
            return self._trees.get(tree_id)

    def list_dialog_trees(
        self,
        npc_id: str = "",
        limit: int = 100,
    ) -> List[DialogTree]:
        """Return dialog trees, optionally filtered by NPC ID."""
        with self._lock:
            items = list(self._trees.values())
        if npc_id:
            items = [t for t in items if t.npc_id == npc_id]
        if limit and limit > 0:
            items = items[:limit]
        return items

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def add_node(
        self,
        tree_id: str,
        node_id: str,
        node_type: Any = DialogNodeType.NPC_LINE,
        speaker_id: str = "",
        text: str = "",
        choices: Optional[List[DialogChoice]] = None,
        next_nodes: Optional[List[str]] = None,
        conditions: Optional[List[DialogCondition]] = None,
        actions: Optional[List[str]] = None,
        mood: Any = DialogMood.NEUTRAL,
        tone: Any = DialogTone.CASUAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, DialogTree]:
        """Add a dialog node to a tree."""
        if not tree_id or not node_id:
            return False, "tree_id and node_id are required", DialogTree(
                tree_id="", name="", npc_id="")

        nt = self._coerce_node_type(node_type)
        nm = self._coerce_mood(mood)
        tn = self._coerce_tone(tone)

        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return False, f"tree_id not found: {tree_id}", DialogTree(
                    tree_id="", name="", npc_id="")
            if node_id in tree.nodes:
                return False, f"node_id already exists: {node_id}", tree
            if len(tree.nodes) >= self._config.max_nodes_per_tree:
                return False, "node capacity for tree reached", tree

            node = DialogNode(
                node_id=node_id,
                node_type=nt,
                speaker_id=speaker_id,
                text=text,
                choices=list(choices or []),
                next_nodes=list(next_nodes or []),
                conditions=list(conditions or []),
                actions=list(actions or []),
                mood=nm,
                tone=tn,
                metadata=dict(metadata or {}),
            )
            tree.nodes[node_id] = node
            # Auto-set root node if the tree has none
            if not tree.root_node:
                tree.root_node = node_id
            self._refresh_stats()
            self._emit(
                DialogEventKind.BRANCHED,
                f"Node added to tree {tree.name}: {node_id}",
                data={"tree_id": tree_id, "node_id": node_id,
                      "node_type": nt.value},
            )
            return True, "added", tree

    def remove_node(
        self,
        tree_id: str,
        node_id: str,
    ) -> Tuple[bool, str, DialogTree]:
        """Remove a dialog node from a tree."""
        if not tree_id or not node_id:
            return False, "tree_id and node_id are required", DialogTree(
                tree_id="", name="", npc_id="")
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return False, f"tree_id not found: {tree_id}", DialogTree(
                    tree_id="", name="", npc_id="")
            if node_id not in tree.nodes:
                return False, f"node_id not found: {node_id}", tree
            del tree.nodes[node_id]
            if tree.root_node == node_id:
                # Pick a new root if any nodes remain
                tree.root_node = next(iter(tree.nodes), "")
            self._refresh_stats()
            self._emit(
                DialogEventKind.ENDED,
                f"Node removed from tree {tree.name}: {node_id}",
                data={"tree_id": tree_id, "node_id": node_id},
            )
            return True, "removed", tree

    def get_node(
        self,
        tree_id: str,
        node_id: str,
    ) -> Optional[DialogNode]:
        """Return a dialog node by tree and node ID."""
        if not tree_id or not node_id:
            return None
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return None
            return tree.nodes.get(node_id)

    def list_nodes(self, tree_id: str) -> List[DialogNode]:
        """Return all nodes in a dialog tree."""
        if not tree_id:
            return []
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return []
            return list(tree.nodes.values())

    def set_root_node(
        self,
        tree_id: str,
        node_id: str,
    ) -> Tuple[bool, str, DialogTree]:
        """Set the root (entry) node for a dialog tree."""
        if not tree_id or not node_id:
            return False, "tree_id and node_id are required", DialogTree(
                tree_id="", name="", npc_id="")
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return False, f"tree_id not found: {tree_id}", DialogTree(
                    tree_id="", name="", npc_id="")
            if node_id not in tree.nodes:
                return False, f"node_id not found in tree: {node_id}", tree
            tree.root_node = node_id
            self._emit(
                DialogEventKind.BRANCHED,
                f"Root node set for tree {tree.name}: {node_id}",
                data={"tree_id": tree_id, "root_node": node_id},
            )
            return True, "set", tree

    # ------------------------------------------------------------------
    # Choice Management
    # ------------------------------------------------------------------

    def add_choice(
        self,
        tree_id: str,
        node_id: str,
        choice_id: str,
        text: str,
        next_node: str = "",
        conditions: Optional[List[DialogCondition]] = None,
        requirements: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, DialogNode]:
        """Add a player choice to a dialog node."""
        if not tree_id or not node_id or not choice_id:
            return False, "tree_id, node_id, and choice_id are required", \
                DialogNode(node_id="", node_type=DialogNodeType.NPC_LINE)
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return False, f"tree_id not found: {tree_id}", \
                    DialogNode(node_id="", node_type=DialogNodeType.NPC_LINE)
            node = tree.nodes.get(node_id)
            if node is None:
                return False, f"node_id not found: {node_id}", \
                    DialogNode(node_id="", node_type=DialogNodeType.NPC_LINE)
            # Check for duplicate choice_id within this node
            if any(c.choice_id == choice_id for c in node.choices):
                return False, f"choice_id already exists: {choice_id}", node
            if len(node.choices) >= self._config.max_choices_per_node:
                return False, "choice capacity for node reached", node

            choice = DialogChoice(
                choice_id=choice_id,
                text=text,
                next_node=next_node,
                conditions=list(conditions or []),
                requirements=list(requirements or []),
                metadata=dict(metadata or {}),
            )
            node.choices.append(choice)
            self._emit(
                DialogEventKind.BRANCHED,
                f"Choice added to node {node_id}: {choice_id}",
                data={"tree_id": tree_id, "node_id": node_id,
                      "choice_id": choice_id},
            )
            return True, "added", node

    def remove_choice(
        self,
        tree_id: str,
        node_id: str,
        choice_id: str,
    ) -> Tuple[bool, str, DialogNode]:
        """Remove a player choice from a dialog node."""
        if not tree_id or not node_id or not choice_id:
            return False, "tree_id, node_id, and choice_id are required", \
                DialogNode(node_id="", node_type=DialogNodeType.NPC_LINE)
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return False, f"tree_id not found: {tree_id}", \
                    DialogNode(node_id="", node_type=DialogNodeType.NPC_LINE)
            node = tree.nodes.get(node_id)
            if node is None:
                return False, f"node_id not found: {node_id}", \
                    DialogNode(node_id="", node_type=DialogNodeType.NPC_LINE)
            original_len = len(node.choices)
            node.choices = [c for c in node.choices if c.choice_id != choice_id]
            if len(node.choices) == original_len:
                return False, f"choice_id not found: {choice_id}", node
            self._emit(
                DialogEventKind.ENDED,
                f"Choice removed from node {node_id}: {choice_id}",
                data={"tree_id": tree_id, "node_id": node_id,
                      "choice_id": choice_id},
            )
            return True, "removed", node

    def list_choices(
        self,
        tree_id: str,
        node_id: str,
    ) -> List[DialogChoice]:
        """Return all choices on a dialog node."""
        if not tree_id or not node_id:
            return []
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return []
            node = tree.nodes.get(node_id)
            if node is None:
                return []
            return list(node.choices)

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self,
        tree_id: str,
        player_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[DialogSession]]:
        """Start a new dialog session for a player against a tree."""
        if not tree_id or not player_id:
            return False, "tree_id and player_id are required", None
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return False, f"tree_id not found: {tree_id}", None
            if not tree.root_node:
                return False, "tree has no root node", None
            if len(self._sessions) >= self._config.max_sessions:
                return False, "session capacity reached", None

            session_id = _new_id("ses")
            session = DialogSession(
                session_id=session_id,
                tree_id=tree_id,
                player_id=player_id,
                current_node=tree.root_node,
                mood=tree.start_mood,
                relationship=tree.start_relationship,
                sentiment=DialogSentiment.NEUTRAL,
                topics_discussed=[],
                choices_made=[],
                started_at=_now_ts(),
                status=DialogStatus.ACTIVE,
                metadata=dict(metadata or {}),
            )
            self._sessions[session_id] = session
            self._refresh_stats()
            self._emit(
                DialogEventKind.STARTED,
                f"Session started: player={player_id}, tree={tree.name}",
                session_id=session_id,
                data={"tree_id": tree_id, "player_id": player_id},
            )
            return True, "started", session

    def end_session(self, session_id: str) -> Tuple[bool, str, DialogSession]:
        """End an active or paused dialog session."""
        if not session_id:
            return False, "session_id is required", DialogSession(
                session_id="", tree_id="", player_id="")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", \
                    DialogSession(session_id="", tree_id="", player_id="")
            session.status = DialogStatus.ENDED
            self._refresh_stats()
            self._emit(
                DialogEventKind.ENDED,
                f"Session ended: {session_id}",
                session_id=session_id,
                data={"session_id": session_id},
            )
            return True, "ended", session

    def pause_session(self, session_id: str) -> Tuple[bool, str, DialogSession]:
        """Pause an active dialog session."""
        if not session_id:
            return False, "session_id is required", DialogSession(
                session_id="", tree_id="", player_id="")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", \
                    DialogSession(session_id="", tree_id="", player_id="")
            if session.status != DialogStatus.ACTIVE:
                return False, f"session is not active (status={session.status.value})", \
                    session
            session.status = DialogStatus.PAUSED
            self._refresh_stats()
            self._emit(
                DialogEventKind.MOOD_UPDATED,
                f"Session paused: {session_id}",
                session_id=session_id,
                data={"session_id": session_id},
            )
            return True, "paused", session

    def resume_session(self, session_id: str) -> Tuple[bool, str, DialogSession]:
        """Resume a paused dialog session."""
        if not session_id:
            return False, "session_id is required", DialogSession(
                session_id="", tree_id="", player_id="")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", \
                    DialogSession(session_id="", tree_id="", player_id="")
            if session.status != DialogStatus.PAUSED:
                return False, f"session is not paused (status={session.status.value})", \
                    session
            session.status = DialogStatus.ACTIVE
            self._refresh_stats()
            self._emit(
                DialogEventKind.STARTED,
                f"Session resumed: {session_id}",
                session_id=session_id,
                data={"session_id": session_id},
            )
            return True, "resumed", session

    def get_session(self, session_id: str) -> Optional[DialogSession]:
        """Return a dialog session by ID, or None if not found."""
        if not session_id:
            return None
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(
        self,
        player_id: str = "",
        status: Any = None,
        limit: int = 100,
    ) -> List[DialogSession]:
        """Return dialog sessions, optionally filtered by player and status."""
        st = self._coerce_status(status) if status is not None else None
        with self._lock:
            items = list(self._sessions.values())
        if player_id:
            items = [s for s in items if s.player_id == player_id]
        if st is not None:
            items = [s for s in items if s.status == st]
        if limit and limit > 0:
            items = items[:limit]
        return items

    # ------------------------------------------------------------------
    # Dialog Interaction
    # ------------------------------------------------------------------

    def get_current_node(self, session_id: str) -> Optional[DialogNode]:
        """Return the current dialog node for a session."""
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            tree = self._trees.get(session.tree_id)
            if tree is None:
                return None
            return tree.nodes.get(session.current_node)

    def get_available_choices(self, session_id: str) -> List[DialogChoice]:
        """Return the choices available on the current node.

        Choices are filtered by condition evaluation and flag requirements.
        """
        if not session_id:
            return []
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            tree = self._trees.get(session.tree_id)
            if tree is None:
                return []
            node = tree.nodes.get(session.current_node)
            if node is None:
                return []
            context = self._contexts.get(session_id)
            available: List[DialogChoice] = []
            for choice in node.choices:
                if not self._evaluate_conditions(choice.conditions, session, context):
                    continue
                if not self._check_requirements(choice.requirements, session):
                    continue
                available.append(choice)
            return available

    def select_choice(
        self,
        session_id: str,
        choice_id: str,
    ) -> Tuple[bool, str, Optional[DialogNode]]:
        """Select a choice and advance the dialog to the next node."""
        if not session_id or not choice_id:
            return False, "session_id and choice_id are required", None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", None
            if session.status != DialogStatus.ACTIVE:
                return False, f"session is not active (status={session.status.value})", \
                    None
            tree = self._trees.get(session.tree_id)
            if tree is None:
                return False, "tree not found for session", None
            node = tree.nodes.get(session.current_node)
            if node is None:
                return False, "current node not found", None

            # Find the choice
            choice: Optional[DialogChoice] = None
            for c in node.choices:
                if c.choice_id == choice_id:
                    choice = c
                    break
            if choice is None:
                return False, f"choice_id not found: {choice_id}", None

            # Evaluate conditions
            context = self._contexts.get(session_id)
            if not self._evaluate_conditions(choice.conditions, session, context):
                return False, "choice conditions not met", None
            if not self._check_requirements(choice.requirements, session):
                return False, "choice requirements not met", None

            # Record the choice
            session.choices_made.append(choice_id)
            self._stats.total_choices_made += 1

            # Determine the next node
            next_node_id = choice.next_node
            if not next_node_id and node.next_nodes:
                next_node_id = node.next_nodes[0]
            if not next_node_id:
                return False, "choice has no next_node target", None

            next_node = tree.nodes.get(next_node_id)
            if next_node is None:
                return False, f"next_node not found in tree: {next_node_id}", None

            # Advance the session
            session.current_node = next_node_id

            # Apply mood and tone from the new node
            session.mood = next_node.mood
            self._stats.total_choices_made += 0  # already counted above

            # Execute actions on the new node
            flags = session.metadata.get("flags", {})
            if not isinstance(flags, dict):
                flags = {}
            for action in next_node.actions:
                self._execute_action(action, session, flags)
            session.metadata["flags"] = flags

            # If the next node is an end node, end the session
            if next_node.node_type == DialogNodeType.END:
                session.status = DialogStatus.ENDED
                self._refresh_stats()

            self._emit(
                DialogEventKind.BRANCHED,
                f"Choice selected: {choice_id} -> {next_node_id}",
                session_id=session_id,
                data={"choice_id": choice_id, "next_node": next_node_id},
            )
            return True, "advanced", next_node

    def _execute_action(
        self,
        action: str,
        session: DialogSession,
        flags: Dict[str, Any],
    ) -> None:
        """Execute a single action string on the session state.

        Action format: 'set_flag:flag_name' or 'set_flag:flag_name:value'
        or 'add_topic:topic_name' or 'set_mood:mood_value' or
        'set_relationship:relationship_value'.
        """
        parts = action.split(":", 2)
        if len(parts) < 2:
            return
        verb = parts[0].strip().lower()
        target = parts[1].strip()
        value_str = parts[2].strip() if len(parts) > 2 else "true"

        if verb == "set_flag":
            flags[target] = value_str.lower() not in ("false", "0", "no", "")
        elif verb == "add_topic":
            if target not in session.topics_discussed:
                session.topics_discussed.append(target)
        elif verb == "set_mood":
            new_mood = self._coerce_mood(target)
            session.mood = new_mood
        elif verb == "set_relationship":
            new_rel = self._coerce_relationship(target)
            session.relationship = new_rel
        elif verb == "add_metadata":
            session.metadata[target] = value_str

    def say_line(
        self,
        session_id: str,
        text: str,
    ) -> Tuple[bool, str, Optional[DialogResponse]]:
        """Process a player line: analyze sentiment, update mood, generate response."""
        if not session_id or not text:
            return False, "session_id and text are required", None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", None
            if session.status != DialogStatus.ACTIVE:
                return False, f"session is not active (status={session.status.value})", \
                    None

            # Analyze the player's sentiment
            analysis = self.analyze_sentiment(text)
            self._stats.total_sentiment_analyses += 1

            # Update the session sentiment
            old_sentiment = session.sentiment
            session.sentiment = analysis.sentiment
            if old_sentiment != analysis.sentiment:
                self._emit(
                    DialogEventKind.SENTIMENT_CHANGED,
                    f"Sentiment changed: {old_sentiment.value} -> "
                    f"{analysis.sentiment.value}",
                    session_id=session_id,
                    data={"old": old_sentiment.value,
                          "new": analysis.sentiment.value,
                          "confidence": analysis.confidence},
                )

            # Update the session mood based on the analysis
            new_mood = self._dominant_mood(analysis.mood_scores, session.mood)
            if new_mood != session.mood:
                old_mood = session.mood
                session.mood = new_mood
                self._emit(
                    DialogEventKind.MOOD_UPDATED,
                    f"Mood updated: {old_mood.value} -> {new_mood.value}",
                    session_id=session_id,
                    data={"old": old_mood.value, "new": new_mood.value},
                )

            # Adjust relationship based on sentiment
            self._adjust_relationship_from_sentiment(session, analysis.sentiment)

            # Generate the NPC response
            ok, msg, response = self.auto_generate_response(session_id, text)
            if not ok:
                return False, msg, None

            self._emit(
                DialogEventKind.RESPONDED,
                f"Player said: {text[:80]}",
                session_id=session_id,
                data={"player_text": text,
                      "sentiment": analysis.sentiment.value,
                      "response_id": response.response_id if response else ""},
            )
            return True, "responded", response

    def _dominant_mood(
        self,
        mood_scores: Dict[str, float],
        fallback: DialogMood,
    ) -> DialogMood:
        """Pick the mood with the highest score, or fallback if none."""
        if not mood_scores:
            return fallback
        best_mood_str = max(mood_scores, key=lambda k: mood_scores[k])
        return self._coerce_mood(best_mood_str, fallback)

    def _adjust_relationship_from_sentiment(
        self,
        session: DialogSession,
        sentiment: DialogSentiment,
    ) -> None:
        """Nudge the session relationship based on player sentiment."""
        rank = _RELATIONSHIP_RANK.get(session.relationship, 2)
        if sentiment == DialogSentiment.VERY_POSITIVE:
            rank = min(rank + 1, 5)
        elif sentiment == DialogSentiment.POSITIVE:
            # Only drift up occasionally to avoid rapid escalation
            if random.random() < 0.3:
                rank = min(rank + 1, 5)
        elif sentiment == DialogSentiment.VERY_NEGATIVE:
            rank = max(rank - 1, 0)
        elif sentiment == DialogSentiment.NEGATIVE:
            if random.random() < 0.3:
                rank = max(rank - 1, 0)

        # Find the relationship matching the new rank
        for rel, r in _RELATIONSHIP_RANK.items():
            if r == rank:
                if session.relationship != rel:
                    old_rel = session.relationship
                    session.relationship = rel
                    self._emit(
                        DialogEventKind.RELATIONSHIP_UPDATED,
                        f"Relationship drifted: {old_rel.value} -> {rel.value}",
                        session_id=session.session_id,
                        data={"old": old_rel.value, "new": rel.value},
                    )
                break

    def get_session_mood(self, session_id: str) -> Optional[DialogMood]:
        """Return the current mood of a session."""
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.mood

    def get_session_relationship(
        self,
        session_id: str,
    ) -> Optional[DialogRelationship]:
        """Return the current relationship standing of a session."""
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.relationship

    # ------------------------------------------------------------------
    # Sentiment Analysis
    # ------------------------------------------------------------------

    def analyze_sentiment(self, text: str) -> SentimentAnalysis:
        """Analyze a piece of player text and return a sentiment breakdown.

        Uses keyword matching against positive and negative word banks to
        derive an overall sentiment score, mood scores, and matched
        keywords.
        """
        if not text:
            return SentimentAnalysis(
                text="",
                sentiment=DialogSentiment.NEUTRAL,
                confidence=0.5,
                mood_scores={},
                keywords=[],
                intensity=0.0,
            )

        lower_text = text.lower()
        words = lower_text.split()

        # Also check multi-word phrases by scanning the raw text
        positive_score = 0.0
        negative_score = 0.0
        matched_keywords: List[str] = []
        mood_scores: Dict[str, float] = {}

        # Check single-word and phrase matches
        all_positive = list(_POSITIVE_WORDS.keys())
        all_negative = list(_NEGATIVE_WORDS.keys())

        for word in all_positive:
            if word in lower_text:
                weight = _POSITIVE_WORDS[word]
                positive_score += weight
                matched_keywords.append(word)

        for word in all_negative:
            if word in lower_text:
                weight = _NEGATIVE_WORDS[word]
                negative_score += weight
                matched_keywords.append(word)

        # Compute mood scores from mood keyword banks
        for mood, keywords in _MOOD_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in lower_text:
                    score += 1.0
            if score > 0:
                # Normalize by the number of matched keywords
                mood_scores[mood.value] = round(
                    _clamp(score / 3.0, 0.0, 1.0), 3)

        # Deduplicate matched keywords while preserving order
        seen = set()
        unique_keywords: List[str] = []
        for kw in matched_keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        # Compute net sentiment score
        total = positive_score + negative_score
        if total == 0:
            net_score = 0.0
            sentiment = DialogSentiment.NEUTRAL
            confidence = 0.5
        else:
            net_score = (positive_score - negative_score) / max(total, 1.0)
            if net_score >= _SENTIMENT_VERY_POS:
                sentiment = DialogSentiment.VERY_POSITIVE
            elif net_score >= _SENTIMENT_POS:
                sentiment = DialogSentiment.POSITIVE
            elif net_score <= _SENTIMENT_VERY_NEG:
                sentiment = DialogSentiment.VERY_NEGATIVE
            elif net_score <= _SENTIMENT_NEG:
                sentiment = DialogSentiment.NEGATIVE
            else:
                sentiment = DialogSentiment.NEUTRAL
            # Confidence scales with how many keywords matched
            confidence = _clamp(
                round(0.5 + min(total * 0.1, 0.49), 2), 0.5, 0.99)

        # Intensity is the absolute magnitude of the net score
        intensity = _clamp(round(abs(net_score), 3), 0.0, 1.0)

        self._stats.total_sentiment_analyses += 1

        return SentimentAnalysis(
            text=text,
            sentiment=sentiment,
            confidence=confidence,
            mood_scores=mood_scores,
            keywords=unique_keywords,
            intensity=intensity,
        )

    def update_session_sentiment(
        self,
        session_id: str,
        text: str,
    ) -> Tuple[bool, str, DialogSession]:
        """Analyze text and update the session's sentiment and mood."""
        if not session_id:
            return False, "session_id is required", DialogSession(
                session_id="", tree_id="", player_id="")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", \
                    DialogSession(session_id="", tree_id="", player_id="")

            analysis = self.analyze_sentiment(text)
            old_sentiment = session.sentiment
            session.sentiment = analysis.sentiment

            if old_sentiment != session.sentiment:
                self._emit(
                    DialogEventKind.SENTIMENT_CHANGED,
                    f"Sentiment updated: {old_sentiment.value} -> "
                    f"{session.sentiment.value}",
                    session_id=session_id,
                    data={"old": old_sentiment.value,
                          "new": session.sentiment.value,
                          "confidence": analysis.confidence},
                )

            # Update mood from the analysis
            new_mood = self._dominant_mood(analysis.mood_scores, session.mood)
            if new_mood != session.mood:
                old_mood = session.mood
                session.mood = new_mood
                self._emit(
                    DialogEventKind.MOOD_UPDATED,
                    f"Mood updated from sentiment: {old_mood.value} -> "
                    f"{new_mood.value}",
                    session_id=session_id,
                    data={"old": old_mood.value, "new": new_mood.value},
                )

            self._adjust_relationship_from_sentiment(
                session, analysis.sentiment)

            return True, "updated", session

    # ------------------------------------------------------------------
    # AI Generation
    # ------------------------------------------------------------------

    def auto_generate_response(
        self,
        session_id: str,
        player_input: str,
    ) -> Tuple[bool, str, Optional[DialogResponse]]:
        """Generate an AI NPC response based on profile, mood, and context."""
        if not session_id:
            return False, "session_id is required", None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", None
            tree = self._trees.get(session.tree_id)
            if tree is None:
                return False, "tree not found for session", None
            npc = self._npc_profiles.get(tree.npc_id)
            if npc is None:
                return False, "npc profile not found for tree", None

            if not self._config.enable_ai_generation:
                # Fallback: return the text of the current node if available
                node = tree.nodes.get(session.current_node)
                fallback_text = node.text if node else "..."
                response = DialogResponse(
                    response_id=_new_id("rsp"),
                    text=fallback_text,
                    mood=session.mood,
                    tone=npc.default_tone,
                    next_node=session.current_node,
                    confidence=0.3,
                    metadata={"source": "fallback"},
                )
                return True, "fallback", response

            # Determine the dominant topic
            topic = self._infer_topic(player_input, tree)

            # Build the response text from templates
            text = self._build_response_text(
                npc=npc,
                mood=session.mood,
                relationship=session.relationship,
                player_input=player_input,
                topic=topic,
            )

            # Compute confidence
            confidence = self._compute_confidence(
                npc=npc,
                mood=session.mood,
                relationship=session.relationship,
                sentiment=session.sentiment,
            )

            response = DialogResponse(
                response_id=_new_id("rsp"),
                text=text,
                mood=session.mood,
                tone=npc.default_tone,
                next_node=session.current_node,
                confidence=confidence,
                metadata={
                    "source": "ai_generated",
                    "voice_style": npc.voice_style.value,
                    "topic": topic.value,
                    "npc_name": npc.name,
                },
            )
            self._response_history.append(response)
            _evict_fifo_list(self._response_history, _MAX_RESPONSE_HISTORY)
            self._stats.total_responses_generated += 1

            # Record the topic if not already discussed
            topic_str = topic.value
            if topic_str not in session.topics_discussed:
                session.topics_discussed.append(topic_str)
                self._emit(
                    DialogEventKind.TOPIC_CHANGED,
                    f"Topic introduced: {topic_str}",
                    session_id=session_id,
                    data={"topic": topic_str},
                )

            self._emit(
                DialogEventKind.RESPONDED,
                f"AI response generated for session {session_id}",
                session_id=session_id,
                data={"response_id": response.response_id,
                      "confidence": confidence,
                      "topic": topic.value},
            )
            return True, "generated", response

    def _infer_topic(
        self,
        player_input: str,
        tree: DialogTree,
    ) -> DialogTopic:
        """Infer the most likely dialog topic from player input and tree."""
        if not player_input:
            # Default to the first topic of the tree, or greeting
            if tree.topics:
                return tree.topics[0]
            return DialogTopic.GREETING
        lower = player_input.lower()
        # Keyword-based topic detection
        topic_keywords: Dict[DialogTopic, List[str]] = {
            DialogTopic.GREETING: ["hello", "hi", "greetings", "hey", "good day"],
            DialogTopic.QUEST: ["quest", "task", "mission", "job", "bounty", "errand"],
            DialogTopic.TRADE: ["buy", "sell", "trade", "price", "cost", "gold", "coin", "ware", "shop"],
            DialogTopic.LORE: ["history", "legend", "story", "tale", "ancient", "old", "past", "myth"],
            DialogTopic.COMBAT: ["fight", "battle", "attack", "enemy", "weapon", "sword", "spell", "kill"],
            DialogTopic.PERSONAL: ["you", "yourself", "family", "life", "who are you", "name"],
            DialogTopic.RUMOR: ["rumor", "heard", "gossip", "word", "news", "whisper"],
            DialogTopic.FAREWELL: ["bye", "farewell", "goodbye", "later", "leave", "go"],
        }
        best_topic = DialogTopic.CUSTOM
        best_score = 0
        for topic, keywords in topic_keywords.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_topic = topic
        if best_score == 0:
            if tree.topics:
                return tree.topics[0]
            return DialogTopic.GREETING
        return best_topic

    def auto_generate_dialog_tree(
        self,
        npc_id: str,
        topic: Any,
        context: Optional[DialogContext] = None,
    ) -> Tuple[bool, str, Optional[DialogTree]]:
        """Generate a full dialog tree from the NPC profile and topic.

        Produces at least 5 nodes: a root greeting, two branching
        choices, two response nodes, and a farewell end node.
        """
        if not npc_id:
            return False, "npc_id is required", None
        with self._lock:
            npc = self._npc_profiles.get(npc_id)
            if npc is None:
                return False, f"npc_id not found: {npc_id}", None
            if not self._config.enable_ai_generation:
                return False, "AI generation is disabled", None

            tp = self._coerce_topic(topic, DialogTopic.GREETING)
            tree_id = _new_id("tree")
            tree_name = f"Auto: {npc.name} - {tp.value}"

            # Determine start mood and relationship from the NPC profile
            start_mood = npc.default_mood
            start_rel = npc.relationship_with_player

            tree = DialogTree(
                tree_id=tree_id,
                name=tree_name,
                npc_id=npc_id,
                root_node="",
                nodes={},
                start_mood=start_mood,
                start_relationship=start_rel,
                topics=[tp],
                metadata={"auto_generated": True, "topic": tp.value},
            )

            # Node 1: Root greeting from the NPC
            root_text = self._build_response_text(
                npc=npc, mood=start_mood, relationship=start_rel,
                player_input="", topic=tp,
            )
            root_node = DialogNode(
                node_id="auto_root",
                node_type=DialogNodeType.NPC_LINE,
                speaker_id=npc_id,
                text=root_text,
                mood=start_mood,
                tone=npc.default_tone,
                metadata={"auto": True, "step": "greeting"},
            )
            tree.nodes["auto_root"] = root_node
            tree.root_node = "auto_root"

            # Node 2: First branch response
            branch_a_text = self._build_response_text(
                npc=npc, mood=DialogMood.CURIOUS, relationship=start_rel,
                player_input="tell me more", topic=tp,
            )
            node_a = DialogNode(
                node_id="auto_branch_a",
                node_type=DialogNodeType.NPC_LINE,
                speaker_id=npc_id,
                text=branch_a_text,
                mood=DialogMood.CURIOUS,
                tone=npc.default_tone,
                metadata={"auto": True, "step": "branch_a"},
            )
            tree.nodes["auto_branch_a"] = node_a

            # Node 3: Second branch response
            branch_b_mood = DialogMood.HAPPY if start_rel != DialogRelationship.HOSTILE else DialogMood.ANGRY
            branch_b_text = self._build_response_text(
                npc=npc, mood=branch_b_mood, relationship=start_rel,
                player_input="let us deal", topic=tp,
            )
            node_b = DialogNode(
                node_id="auto_branch_b",
                node_type=DialogNodeType.NPC_LINE,
                speaker_id=npc_id,
                text=branch_b_text,
                mood=branch_b_mood,
                tone=npc.default_tone,
                metadata={"auto": True, "step": "branch_b"},
            )
            tree.nodes["auto_branch_b"] = node_b

            # Node 4: Deeper detail node
            detail_text = self._build_response_text(
                npc=npc, mood=DialogMood.TRUSTING, relationship=start_rel,
                player_input="I understand", topic=tp,
            )
            node_detail = DialogNode(
                node_id="auto_detail",
                node_type=DialogNodeType.NPC_LINE,
                speaker_id=npc_id,
                text=detail_text,
                mood=DialogMood.TRUSTING,
                tone=npc.default_tone,
                actions=["add_topic:" + tp.value],
                metadata={"auto": True, "step": "detail"},
            )
            tree.nodes["auto_detail"] = node_detail

            # Node 5: Farewell end node
            farewell_text = self._build_response_text(
                npc=npc, mood=start_mood, relationship=start_rel,
                player_input="goodbye", topic=DialogTopic.FAREWELL,
            )
            node_end = DialogNode(
                node_id="auto_end",
                node_type=DialogNodeType.END,
                speaker_id=npc_id,
                text=farewell_text,
                mood=start_mood,
                tone=npc.default_tone,
                metadata={"auto": True, "step": "farewell"},
            )
            tree.nodes["auto_end"] = node_end

            # Wire choices on the root node
            root_node.choices = [
                DialogChoice(
                    choice_id="auto_choice_a",
                    text="Tell me more about this.",
                    next_node="auto_branch_a",
                ),
                DialogChoice(
                    choice_id="auto_choice_b",
                    text="Let us make a deal.",
                    next_node="auto_branch_b",
                ),
                DialogChoice(
                    choice_id="auto_choice_end",
                    text="I must be going. Farewell.",
                    next_node="auto_end",
                ),
            ]

            # Wire choices on branch nodes leading to detail and end
            node_a.choices = [
                DialogChoice(
                    choice_id="auto_a_detail",
                    text="Go on, I am listening.",
                    next_node="auto_detail",
                ),
                DialogChoice(
                    choice_id="auto_a_end",
                    text="Enough. Goodbye.",
                    next_node="auto_end",
                ),
            ]
            node_b.choices = [
                DialogChoice(
                    choice_id="auto_b_detail",
                    text="Tell me the details.",
                    next_node="auto_detail",
                ),
                DialogChoice(
                    choice_id="auto_b_end",
                    text="Not interested. Farewell.",
                    next_node="auto_end",
                ),
            ]
            node_detail.choices = [
                DialogChoice(
                    choice_id="auto_detail_end",
                    text="Thank you. Until next time.",
                    next_node="auto_end",
                ),
            ]

            self._trees[tree_id] = tree
            self._refresh_stats()
            self._emit(
                DialogEventKind.STARTED,
                f"Auto-generated dialog tree: {tree_name}",
                data={"tree_id": tree_id, "npc_id": npc_id,
                      "topic": tp.value, "node_count": len(tree.nodes)},
            )
            return True, "generated", tree

    def suggest_topic(
        self,
        session_id: str,
    ) -> Tuple[bool, str, Optional[str]]:
        """Suggest a topic the player has not yet explored in the session."""
        if not session_id:
            return False, "session_id is required", None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", None
            tree = self._trees.get(session.tree_id)
            if tree is None:
                return False, "tree not found for session", None

            # Gather all known topics from the tree and NPC profile
            npc = self._npc_profiles.get(tree.npc_id)
            candidate_topics: List[DialogTopic] = []
            if tree.topics:
                candidate_topics.extend(tree.topics)
            if npc and npc.known_topics:
                for t in npc.known_topics:
                    if t not in candidate_topics:
                        candidate_topics.append(t)
            # Always include greeting and farewell as fallbacks
            for fallback in (DialogTopic.GREETING, DialogTopic.PERSONAL,
                             DialogTopic.RUMOR, DialogTopic.FAREWELL):
                if fallback not in candidate_topics:
                    candidate_topics.append(fallback)

            discussed = set(session.topics_discussed)
            for topic in candidate_topics:
                if topic.value not in discussed:
                    return True, "suggested", topic.value

            # All topics exhausted; suggest revisiting the first one
            if candidate_topics:
                return True, "suggested", candidate_topics[0].value
            return True, "suggested", DialogTopic.GREETING.value

    def suggest_choice(
        self,
        session_id: str,
    ) -> Tuple[bool, str, Optional[DialogChoice]]:
        """Suggest the best available choice for the player.

        Picks the choice whose target node has the mood closest to the
        NPC default mood, favoring choices that improve relationship.
        """
        if not session_id:
            return False, "session_id is required", None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", None
            tree = self._trees.get(session.tree_id)
            if tree is None:
                return False, "tree not found for session", None
            node = tree.nodes.get(session.current_node)
            if node is None:
                return False, "current node not found", None

            context = self._contexts.get(session_id)
            available: List[DialogChoice] = []
            for choice in node.choices:
                if not self._evaluate_conditions(choice.conditions, session, context):
                    continue
                if not self._check_requirements(choice.requirements, session):
                    continue
                available.append(choice)

            if not available:
                return False, "no available choices", None

            npc = self._npc_profiles.get(tree.npc_id)
            target_mood = npc.default_mood if npc else DialogMood.NEUTRAL

            best_choice: Optional[DialogChoice] = None
            best_score = -1.0
            for choice in available:
                target = tree.nodes.get(choice.next_node)
                score = 0.5
                if target is not None:
                    # Favor nodes whose mood matches the NPC default
                    if target.mood == target_mood:
                        score += 0.3
                    # Favor nodes that are not end nodes (keep conversation going)
                    if target.node_type != DialogNodeType.END:
                        score += 0.2
                    # Favor trusting and happy moods
                    if target.mood in (DialogMood.TRUSTING, DialogMood.HAPPY):
                        score += 0.15
                if score > best_score:
                    best_score = score
                    best_choice = choice

            if best_choice is None:
                best_choice = available[0]
            return True, "suggested", best_choice

    def optimize_dialog_flow(
        self,
        tree_id: str,
    ) -> Tuple[bool, str, List[str]]:
        """Analyze a dialog tree and return a list of optimization suggestions."""
        if not tree_id:
            return False, "tree_id is required", []
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return False, f"tree_id not found: {tree_id}", []

            suggestions: List[str] = []
            node_ids = set(tree.nodes.keys())

            # Check for missing root node
            if not tree.root_node:
                suggestions.append("Tree has no root node set; players cannot start a session.")
            elif tree.root_node not in tree.nodes:
                suggestions.append(
                    f"Root node '{tree.root_node}' does not exist in the tree nodes.")

            # Check each node for issues
            for node in tree.nodes.values():
                # Nodes with no choices and no next_nodes that are not end nodes
                if (node.node_type != DialogNodeType.END
                        and not node.choices
                        and not node.next_nodes):
                    suggestions.append(
                        f"Node '{node.node_id}' has no choices, no next_nodes, "
                        f"and is not an end node (dead end).")

                # End nodes should not have choices
                if node.node_type == DialogNodeType.END and node.choices:
                    suggestions.append(
                        f"Node '{node.node_id}' is an end node but has choices "
                        f"that will never be used.")

                # Check choice next_node targets exist
                for choice in node.choices:
                    if choice.next_node and choice.next_node not in node_ids:
                        suggestions.append(
                            f"Node '{node.node_id}' choice '{choice.choice_id}' "
                            f"points to non-existent node '{choice.next_node}'.")

                # Check next_nodes targets exist
                for nn in node.next_nodes:
                    if nn not in node_ids:
                        suggestions.append(
                            f"Node '{node.node_id}' next_nodes entry '{nn}' "
                            f"does not exist in the tree.")

            # Check for unreachable nodes (nodes not reachable from root)
            if tree.root_node and tree.root_node in tree.nodes:
                reachable: set = set()
                stack: List[str] = [tree.root_node]
                while stack:
                    nid = stack.pop()
                    if nid in reachable:
                        continue
                    reachable.add(nid)
                    n = tree.nodes.get(nid)
                    if n is None:
                        continue
                    for c in n.choices:
                        if c.next_node and c.next_node not in reachable:
                            stack.append(c.next_node)
                    for nn in n.next_nodes:
                        if nn not in reachable:
                            stack.append(nn)
                for nid in node_ids:
                    if nid not in reachable:
                        suggestions.append(
                            f"Node '{nid}' is unreachable from the root node.")

            # Check for empty text on npc_line nodes
            for node in tree.nodes.values():
                if node.node_type == DialogNodeType.NPC_LINE and not node.text:
                    suggestions.append(
                        f"Node '{node.node_id}' is an npc_line with empty text.")

            if not suggestions:
                suggestions.append("No issues found; dialog flow looks clean.")
            return True, "analyzed", suggestions

    # ------------------------------------------------------------------
    # Context Management
    # ------------------------------------------------------------------

    def set_dialog_context(
        self,
        session_id: str,
        context: DialogContext,
    ) -> Tuple[bool, str, DialogSession]:
        """Attach a world-state context to a session for richer responses."""
        if not session_id:
            return False, "session_id is required", DialogSession(
                session_id="", tree_id="", player_id="")
        if not isinstance(context, DialogContext):
            return False, "context must be a DialogContext instance", DialogSession(
                session_id="", tree_id="", player_id="")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_id not found: {session_id}", \
                    DialogSession(session_id="", tree_id="", player_id="")
            self._contexts[session_id] = context
            # Sync reputation into session metadata for condition checks
            session.metadata["reputation"] = context.player_reputation
            self._emit(
                DialogEventKind.MOOD_UPDATED,
                f"Context set for session {session_id}",
                session_id=session_id,
                data={"location": context.location,
                      "time_of_day": context.time_of_day,
                      "reputation": context.player_reputation},
            )
            return True, "set", session

    def get_dialog_context(self, session_id: str) -> Optional[DialogContext]:
        """Return the context attached to a session, or None."""
        if not session_id:
            return None
        with self._lock:
            return self._contexts.get(session_id)

    # ------------------------------------------------------------------
    # System Management
    # ------------------------------------------------------------------

    def get_config(self) -> DialogConfig:
        """Return the current director configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, DialogConfig]:
        """Apply configuration updates passed as keyword arguments."""
        with self._lock:
            if not kwargs:
                return False, "no updates provided", self._config
            for key, value in kwargs.items():
                if key == "metadata" and isinstance(value, dict):
                    continue
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
            self._emit(
                DialogEventKind.MOOD_UPDATED,
                f"Config updated: {list(kwargs.keys())}",
                data={"keys": list(kwargs.keys())},
            )
            return True, "updated", self._config

    def get_stats(self) -> DialogStats:
        """Return aggregate statistics as a DialogStats dataclass."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> DialogSnapshot:
        """Return a full state snapshot as a DialogSnapshot dataclass."""
        with self._lock:
            self._refresh_stats()
            current_moods: Dict[str, str] = {}
            for sid, session in self._sessions.items():
                if session.status == DialogStatus.ACTIVE:
                    current_moods[sid] = session.mood.value
            return DialogSnapshot(
                initialized=self._initialized,
                tick_count=self._tick_count,
                active_sessions=self._stats.active_sessions,
                total_trees=self._stats.total_trees,
                total_npcs=self._stats.total_npcs,
                current_moods=current_moods,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a dictionary summarizing the current director state."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "npc_profiles": len(self._npc_profiles),
                "trees": len(self._trees),
                "sessions": len(self._sessions),
                "active_sessions": self._stats.active_sessions,
                "contexts": len(self._contexts),
                "events": len(self._events),
                "response_history": len(self._response_history),
                "tick_count": self._tick_count,
                "total_nodes": self._stats.total_nodes,
                "total_responses_generated": self._stats.total_responses_generated,
                "total_choices_made": self._stats.total_choices_made,
                "total_sentiment_analyses": self._stats.total_sentiment_analyses,
            }

    def list_events(self, limit: int = 100) -> List[DialogEvent]:
        """Return the most recent dialog events, up to limit."""
        with self._lock:
            items = list(self._events)
        if limit and limit > 0:
            items = items[-limit:]
        return items

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the director by one tick.

        Handles session timeouts (pausing inactive sessions), mood decay
        toward neutral, and relationship drift toward neutral.
        """
        with self._lock:
            self._tick_count += 1
            now = _now_ts()
            timeout = self._config.response_timeout
            timed_out = 0
            moods_decayed = 0
            relationships_drifted = 0

            for session in self._sessions.values():
                # Session timeout: pause sessions inactive beyond the timeout
                if session.status == DialogStatus.ACTIVE:
                    idle = now - session.started_at
                    # Use the last activity time if tracked, else started_at
                    last_activity = session.metadata.get("last_activity",
                                                         session.started_at)
                    idle = now - last_activity
                    if idle > timeout:
                        session.status = DialogStatus.PAUSED
                        timed_out += 1
                        self._emit(
                            DialogEventKind.MOOD_UPDATED,
                            f"Session timed out (idle {idle:.0f}s): {session.session_id}",
                            session_id=session.session_id,
                            data={"idle_seconds": idle},
                        )

                # Mood decay toward neutral
                if session.mood != DialogMood.NEUTRAL:
                    old_mood = session.mood
                    session.mood = self._decay_mood(session.mood)
                    if session.mood != old_mood:
                        moods_decayed += 1

                # Relationship drift toward neutral
                if session.relationship != DialogRelationship.NEUTRAL:
                    old_rel = session.relationship
                    session.relationship = self._drift_relationship(session.relationship)
                    if session.relationship != old_rel:
                        relationships_drifted += 1

            self._refresh_stats()
            return {
                "tick": self._tick_count,
                "dt": dt,
                "timed_out": timed_out,
                "moods_decayed": moods_decayed,
                "relationships_drifted": relationships_drifted,
                "active_sessions": self._stats.active_sessions,
                "total_sessions": self._stats.total_sessions,
                "total_trees": self._stats.total_trees,
                "total_npcs": self._stats.total_npcs,
            }

    def reset(self) -> Tuple[bool, str]:
        """Clear all director state and re-seed the canonical dataset."""
        with self._lock:
            self._npc_profiles.clear()
            self._trees.clear()
            self._sessions.clear()
            self._contexts.clear()
            self._events.clear()
            self._response_history.clear()
            self._config = DialogConfig()
            self._stats = DialogStats()
            self._tick_count = 0
            self._initialized = False
            self._seed()
            return True, "reset"

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the director with a canonical set of dialog content."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # ----------------------------------------------------------
            # NPC Profiles (5): tavern keeper, quest giver, merchant,
            # guard captain, mysterious stranger
            # ----------------------------------------------------------
            self._seed_npc_profiles()

            # ----------------------------------------------------------
            # Dialog Trees (4): greeting, quest, trade, lore
            # Each with 8+ nodes
            # ----------------------------------------------------------
            self._seed_greeting_tree()
            self._seed_quest_tree()
            self._seed_trade_tree()
            self._seed_lore_tree()

            # ----------------------------------------------------------
            # Sessions (10) spanning the four trees
            # ----------------------------------------------------------
            self._seed_sessions()

            # ----------------------------------------------------------
            # Events (6) for the initial timeline
            # ----------------------------------------------------------
            self._seed_events()

            self._refresh_stats()
            self._emit(
                DialogEventKind.STARTED,
                "Dialog director seeded",
                data={
                    "npcs": len(self._npc_profiles),
                    "trees": len(self._trees),
                    "sessions": len(self._sessions),
                    "events": len(self._events),
                },
            )
            self._initialized = True

    def _seed_npc_profiles(self) -> None:
        """Create the five canonical NPC dialog profiles."""
        # 1. Tavern Keeper - Brilda Copperkettle
        self._npc_profiles["npc_tavern_keeper"] = NPCDialogProfile(
            npc_id="npc_tavern_keeper",
            name="Brilda Copperkettle",
            voice_style=VoiceStyle.MERCHANT,
            personality_traits=["warm", "gossipy", "maternal", "shrewd"],
            default_mood=DialogMood.HAPPY,
            default_tone=DialogTone.CASUAL,
            vocabulary_level=2,
            catchphrases=["Mind your mug!", "Ale's on the house!"],
            backstory_summary=(
                "Brilda has run the Copper Tankard tavern for thirty years. "
                "She knows every traveler who passes through and trades "
                "gossip as freely as she pours ale."),
            relationship_with_player=DialogRelationship.FRIENDLY,
            known_topics=[DialogTopic.GREETING, DialogTopic.RUMOR,
                          DialogTopic.PERSONAL, DialogTopic.FAREWELL],
            metadata={"location": "copper_tankard_tavern"},
        )

        # 2. Quest Giver - Captain Aldric Vane
        self._npc_profiles["npc_quest_giver"] = NPCDialogProfile(
            npc_id="npc_quest_giver",
            name="Captain Aldric Vane",
            voice_style=VoiceStyle.WARRIOR,
            personality_traits=["stern", "dutiful", "brave", "pragmatic"],
            default_mood=DialogMood.NEUTRAL,
            default_tone=DialogTone.FORMAL,
            vocabulary_level=2,
            catchphrases=["Steel yourself.", "The realm demands it."],
            backstory_summary=(
                "A career soldier turned quest coordinator, Aldric assigns "
                "bounties and missions to capable adventurers. He values "
                "discipline and results above all else."),
            relationship_with_player=DialogRelationship.NEUTRAL,
            known_topics=[DialogTopic.QUEST, DialogTopic.COMBAT,
                          DialogTopic.FAREWELL],
            metadata={"location": "guard_headquarters"},
        )

        # 3. Merchant - Silas Goldhand
        self._npc_profiles["npc_merchant"] = NPCDialogProfile(
            npc_id="npc_merchant",
            name="Silas Goldhand",
            voice_style=VoiceStyle.MERCHANT,
            personality_traits=["persuasive", "greedy", "charming", "cunning"],
            default_mood=DialogMood.HAPPY,
            default_tone=DialogTone.DIPLOMATIC,
            vocabulary_level=3,
            catchphrases=["A bargain at twice the price!",
                          "For you, a special discount!"],
            backstory_summary=(
                "Silas traveled the trade routes for decades before "
                "settling to run his Emporium. He has a nose for profit "
                "and a silver tongue for closing deals."),
            relationship_with_player=DialogRelationship.FRIENDLY,
            known_topics=[DialogTopic.TRADE, DialogTopic.RUMOR,
                          DialogTopic.FAREWELL],
            metadata={"location": "goldhand_emporium"},
        )

        # 4. Guard Captain - Sergeant Maren Ironfell
        self._npc_profiles["npc_guard_captain"] = NPCDialogProfile(
            npc_id="npc_guard_captain",
            name="Sergeant Maren Ironfell",
            voice_style=VoiceStyle.ROYAL,
            personality_traits=["authoritative", "loyal", "suspicious",
                                "disciplined"],
            default_mood=DialogMood.NEUTRAL,
            default_tone=DialogTone.FORMAL,
            vocabulary_level=2,
            catchphrases=["By the crown's authority.", "Stand down."],
            backstory_summary=(
                "Maren commands the city guard with an iron fist. She "
                "protects the peace and answers directly to the throne, "
                "trusting few outside her ranks."),
            relationship_with_player=DialogRelationship.NEUTRAL,
            known_topics=[DialogTopic.COMBAT, DialogTopic.PERSONAL,
                          DialogTopic.FAREWELL],
            metadata={"location": "city_barracks"},
        )

        # 5. Mysterious Stranger - The Hooded Wanderer
        self._npc_profiles["npc_mysterious_stranger"] = NPCDialogProfile(
            npc_id="npc_mysterious_stranger",
            name="The Hooded Wanderer",
            voice_style=VoiceStyle.VILLAIN,
            personality_traits=["enigmatic", "cryptic", "wise", "ominous"],
            default_mood=DialogMood.SUSPICIOUS,
            default_tone=DialogTone.MYSTERIOUS,
            vocabulary_level=3,
            catchphrases=["The threads of fate weave strangely.",
                          "All will be revealed... in time."],
            backstory_summary=(
                "Nobody knows the Wanderer's true name or origin. He "
                "appears when great events stir, speaks in riddles, and "
                "vanishes before dawn. Some say he is a keeper of "
                "forbidden knowledge."),
            relationship_with_player=DialogRelationship.UNFRIENDLY,
            known_topics=[DialogTopic.LORE, DialogTopic.PERSONAL,
                          DialogTopic.FAREWELL],
            metadata={"location": "unknown"},
        )

    def _seed_greeting_tree(self) -> None:
        """Create the greeting dialog tree for the tavern keeper (8 nodes)."""
        tree = DialogTree(
            tree_id="tree_greeting",
            name="Tavern Greeting",
            npc_id="npc_tavern_keeper",
            root_node="greet_root",
            nodes={},
            start_mood=DialogMood.HAPPY,
            start_relationship=DialogRelationship.FRIENDLY,
            topics=[DialogTopic.GREETING, DialogTopic.RUMOR,
                    DialogTopic.PERSONAL],
            metadata={"location": "copper_tankard_tavern"},
        )

        # Root node: tavern keeper greets the player
        tree.nodes["greet_root"] = DialogNode(
            node_id="greet_root",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_tavern_keeper",
            text=("Welcome to the Copper Tankard, traveler! Pull up a stool. "
                  "What can old Brilda get for you?"),
            mood=DialogMood.HAPPY,
            tone=DialogTone.CASUAL,
            choices=[
                DialogChoice(choice_id="greet_casual",
                             text="Just passing through.",
                             next_node="greet_casual_resp"),
                DialogChoice(choice_id="greet_news",
                             text="What's the news today?",
                             next_node="greet_news_resp"),
                DialogChoice(choice_id="greet_room",
                             text="I need a room for the night.",
                             next_node="greet_room_resp"),
            ],
        )

        # Casual response
        tree.nodes["greet_casual_resp"] = DialogNode(
            node_id="greet_casual_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_tavern_keeper",
            text=("Fair enough. The road's long, isn't it? Rest your feet a "
                  "while. Ale's cold and the fire's warm."),
            mood=DialogMood.HAPPY,
            tone=DialogTone.CASUAL,
            choices=[
                DialogChoice(choice_id="greet_casual_thanks",
                             text="Thanks, Brilda.",
                             next_node="greet_farewell"),
            ],
        )

        # News response
        tree.nodes["greet_news_resp"] = DialogNode(
            node_id="greet_news_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_tavern_keeper",
            text=("Heard the goblins are restless near the old mill. And "
                  "there's talk of a hooded stranger asking about you. "
                  "Trouble follows you, doesn't it?"),
            mood=DialogMood.CURIOUS,
            tone=DialogTone.CASUAL,
            choices=[
                DialogChoice(choice_id="greet_stranger",
                             text="A stranger? Tell me more.",
                             next_node="greet_stranger_resp"),
                DialogChoice(choice_id="greet_goblins",
                             text="Goblins, you say?",
                             next_node="greet_goblins_resp"),
            ],
        )

        # Room response
        tree.nodes["greet_room_resp"] = DialogNode(
            node_id="greet_room_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_tavern_keeper",
            text=("Five silver a night, breakfast included. The beds are "
                  "clean and the walls are thick. Deal?"),
            mood=DialogMood.HAPPY,
            tone=DialogTone.CASUAL,
            choices=[
                DialogChoice(choice_id="greet_room_yes",
                             text="Deal. I'll take it.",
                             next_node="greet_room_yes_resp"),
                DialogChoice(choice_id="greet_room_no",
                             text="Maybe later.",
                             next_node="greet_farewell"),
            ],
        )

        # Stranger detail
        tree.nodes["greet_stranger_resp"] = DialogNode(
            node_id="greet_stranger_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_tavern_keeper",
            text=("Cloaked figure, been here since dawn. Sits in the corner, "
                  "asks questions, pays for nothing. I'd be careful if I "
                  "were you. There's something off about that one."),
            mood=DialogMood.SUSPICIOUS,
            tone=DialogTone.CASUAL,
            actions=["set_flag:mentioned_stranger"],
            choices=[
                DialogChoice(choice_id="greet_stranger_ok",
                             text="I'll keep that in mind.",
                             next_node="greet_farewell"),
            ],
        )

        # Goblins detail
        tree.nodes["greet_goblins_resp"] = DialogNode(
            node_id="greet_goblins_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_tavern_keeper",
            text=("Aye, raiding caravans again. Hit a grain shipment last "
                  "week. Guard captain's looking for hands, if you're the "
                  "adventurous sort. Could earn some coin and some favor."),
            mood=DialogMood.CURIOUS,
            tone=DialogTone.CASUAL,
            actions=["set_flag:mentioned_goblins"],
            choices=[
                DialogChoice(choice_id="greet_goblins_maybe",
                             text="I might be. Where do I find her?",
                             next_node="greet_farewell"),
            ],
        )

        # Room accepted
        tree.nodes["greet_room_yes_resp"] = DialogNode(
            node_id="greet_room_yes_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_tavern_keeper",
            text=("Splendid! Room's upstairs, second door on the left. "
                  "Breakfast is at dawn. Sleep well, traveler."),
            mood=DialogMood.HAPPY,
            tone=DialogTone.CASUAL,
            actions=["set_flag:has_room"],
            choices=[
                DialogChoice(choice_id="greet_room_thanks",
                             text="Thank you, Brilda.",
                             next_node="greet_farewell"),
            ],
        )

        # Farewell end node
        tree.nodes["greet_farewell"] = DialogNode(
            node_id="greet_farewell",
            node_type=DialogNodeType.END,
            speaker_id="npc_tavern_keeper",
            text=("Safe travels, friend. Come back anytime. The Tankard's "
                  "always open for you."),
            mood=DialogMood.HAPPY,
            tone=DialogTone.CASUAL,
        )

        self._trees[tree.tree_id] = tree

    def _seed_quest_tree(self) -> None:
        """Create the quest dialog tree for the quest giver (8 nodes)."""
        tree = DialogTree(
            tree_id="tree_quest",
            name="The Mill Ledger Quest",
            npc_id="npc_quest_giver",
            root_node="quest_root",
            nodes={},
            start_mood=DialogMood.NEUTRAL,
            start_relationship=DialogRelationship.NEUTRAL,
            topics=[DialogTopic.QUEST, DialogTopic.COMBAT],
            metadata={"location": "guard_headquarters"},
        )

        # Root: Aldric addresses the player
        tree.nodes["quest_root"] = DialogNode(
            node_id="quest_root",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_quest_giver",
            text=("You there. You look capable. I have a task that needs "
                  "doing, and I do not ask idly. Are you willing to hear me out?"),
            mood=DialogMood.NEUTRAL,
            tone=DialogTone.FORMAL,
            choices=[
                DialogChoice(choice_id="quest_listen",
                             text="I'm listening.",
                             next_node="quest_brief"),
                DialogChoice(choice_id="quest_decline",
                             text="Not interested.",
                             next_node="quest_decline_resp"),
            ],
        )

        # Briefing
        tree.nodes["quest_brief"] = DialogNode(
            node_id="quest_brief",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_quest_giver",
            text=("Goblins have taken the old mill east of the river. They "
                  "hold a stolen ledger there, names of our scouts. Retrieve "
                  "it. The lives of good people depend on those pages."),
            mood=DialogMood.NEUTRAL,
            tone=DialogTone.FORMAL,
            choices=[
                DialogChoice(choice_id="quest_pay",
                             text="What's the pay?",
                             next_node="quest_pay_resp"),
                DialogChoice(choice_id="quest_accept",
                             text="Consider it done.",
                             next_node="quest_accept_resp"),
            ],
        )

        # Decline
        tree.nodes["quest_decline_resp"] = DialogNode(
            node_id="quest_decline_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_quest_giver",
            text=("A pity. The realm could use more like you. The offer "
                  "stands, should you change your mind. Do not take too long."),
            mood=DialogMood.SAD,
            tone=DialogTone.FORMAL,
            choices=[
                DialogChoice(choice_id="quest_decline_end",
                             text="Maybe later.",
                             next_node="quest_end"),
            ],
        )

        # Pay discussion
        tree.nodes["quest_pay_resp"] = DialogNode(
            node_id="quest_pay_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_quest_giver",
            text=("Fifty gold now, fifty on delivery of the ledger. The "
                  "coin is fair for the risk. Do we have an accord?"),
            mood=DialogMood.NEUTRAL,
            tone=DialogTone.FORMAL,
            choices=[
                DialogChoice(choice_id="quest_pay_agree",
                             text="Agreed.",
                             next_node="quest_accept_resp"),
                DialogChoice(choice_id="quest_pay_negotiate",
                             text="Too little for the danger.",
                             next_node="quest_negotiate_resp"),
            ],
        )

        # Negotiate
        tree.nodes["quest_negotiate_resp"] = DialogNode(
            node_id="quest_negotiate_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_quest_giver",
            text=("Seventy-five now, seventy-five after. That is my final "
                  "offer. Push further and I will find another. Do not test "
                  "my patience."),
            mood=DialogMood.ANGRY,
            tone=DialogTone.AGGRESSIVE,
            choices=[
                DialogChoice(choice_id="quest_negotiate_deal",
                             text="Deal.",
                             next_node="quest_accept_resp"),
            ],
        )

        # Accept
        tree.nodes["quest_accept_resp"] = DialogNode(
            node_id="quest_accept_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_quest_giver",
            text=("Good. The mill is east, past the river bridge. Do not "
                  "tarry. The longer they hold that ledger, the more scouts "
                  "are in danger. One more thing: their leader is cunning. "
                  "Do not underestimate her."),
            mood=DialogMood.NEUTRAL,
            tone=DialogTone.FORMAL,
            actions=["set_flag:quest_accepted",
                     "add_topic:quest",
                     "add_topic:combat"],
            choices=[
                DialogChoice(choice_id="quest_accept_go",
                             text="I won't fail.",
                             next_node="quest_end"),
            ],
        )

        # Warning node (conditional on quest_accepted flag)
        tree.nodes["quest_warning"] = DialogNode(
            node_id="quest_warning",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_quest_giver",
            text=("I forgot to mention: the goblin shaman travels with them. "
                  "She wields fire magic. Carry cold iron or a ward, or you "
                  "will not return."),
            mood=DialogMood.FEARFUL,
            tone=DialogTone.FORMAL,
            conditions=[DialogCondition(
                condition_type="flag", parameter="quest_accepted",
                operator="eq", value=True)],
            choices=[
                DialogChoice(choice_id="quest_warning_ok",
                             text="Understood. Thank you.",
                             next_node="quest_end"),
            ],
        )

        # End node
        tree.nodes["quest_end"] = DialogNode(
            node_id="quest_end",
            node_type=DialogNodeType.END,
            speaker_id="npc_quest_giver",
            text="Go, then. And good hunting. The realm remembers its heroes.",
            mood=DialogMood.NEUTRAL,
            tone=DialogTone.FORMAL,
        )

        self._trees[tree.tree_id] = tree

    def _seed_trade_tree(self) -> None:
        """Create the trade dialog tree for the merchant (9 nodes)."""
        tree = DialogTree(
            tree_id="tree_trade",
            name="Goldhand Emporium Trade",
            npc_id="npc_merchant",
            root_node="trade_root",
            nodes={},
            start_mood=DialogMood.HAPPY,
            start_relationship=DialogRelationship.FRIENDLY,
            topics=[DialogTopic.TRADE, DialogTopic.RUMOR],
            metadata={"location": "goldhand_emporium"},
        )

        # Root: Silas greets a customer
        tree.nodes["trade_root"] = DialogNode(
            node_id="trade_root",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("Ah, a customer! Welcome to Silas Goldhand's Emporium, "
                  "finest goods this side of the capital! What can I do for "
                  "you today, my friend?"),
            mood=DialogMood.HAPPY,
            tone=DialogTone.DIPLOMATIC,
            choices=[
                DialogChoice(choice_id="trade_wares",
                             text="Show me your wares.",
                             next_node="trade_wares_resp"),
                DialogChoice(choice_id="trade_browse",
                             text="Just browsing.",
                             next_node="trade_browse_resp"),
            ],
        )

        # Wares display
        tree.nodes["trade_wares_resp"] = DialogNode(
            node_id="trade_wares_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("Potions, scrolls, rare reagents, I have it all! What "
                  "catches your eye, my discerning friend?"),
            mood=DialogMood.HAPPY,
            tone=DialogTone.DIPLOMATIC,
            choices=[
                DialogChoice(choice_id="trade_potions",
                             text="Health potions.",
                             next_node="trade_potions_resp"),
                DialogChoice(choice_id="trade_scrolls",
                             text="Scrolls.",
                             next_node="trade_scrolls_resp"),
                DialogChoice(choice_id="trade_rare",
                             text="Something rare.",
                             next_node="trade_rare_resp"),
            ],
        )

        # Browsing
        tree.nodes["trade_browse_resp"] = DialogNode(
            node_id="trade_browse_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("Of course, of course! Take your time. But remember, rare "
                  "items do not wait for the indecisive! Another buyer could "
                  "walk in at any moment."),
            mood=DialogMood.HAPPY,
            tone=DialogTone.DIPLOMATIC,
            choices=[
                DialogChoice(choice_id="trade_browse_show",
                             text="Let me see the wares.",
                             next_node="trade_wares_resp"),
                DialogChoice(choice_id="trade_browse_later",
                             text="Maybe another time.",
                             next_node="trade_end"),
            ],
        )

        # Potions
        tree.nodes["trade_potions_resp"] = DialogNode(
            node_id="trade_potions_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("Excellent choice! Three health potions for ten gold, a "
                  "steal at that price. Brewed fresh this morning by a "
                  "certified alchemist. How many would you like?"),
            mood=DialogMood.HAPPY,
            tone=DialogTone.DIPLOMATIC,
            choices=[
                DialogChoice(choice_id="trade_potions_buy",
                             text="I'll take three.",
                             next_node="trade_buy_resp"),
                DialogChoice(choice_id="trade_potions_haggle",
                             text="Too pricey for me.",
                             next_node="trade_haggle_resp"),
            ],
        )

        # Scrolls
        tree.nodes["trade_scrolls_resp"] = DialogNode(
            node_id="trade_scrolls_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("Ah, a student of the arcane! Fireball scrolls, twenty "
                  "gold each. Careful now, do not burn yourself, or my shop! "
                  "I have no insurance against amateur pyromancy."),
            mood=DialogMood.HAPPY,
            tone=DialogTone.HUMOROUS,
            choices=[
                DialogChoice(choice_id="trade_scrolls_buy",
                             text="One, please.",
                             next_node="trade_buy_resp"),
                DialogChoice(choice_id="trade_scrolls_haggle",
                             text="Too expensive.",
                             next_node="trade_haggle_resp"),
            ],
        )

        # Rare item
        tree.nodes["trade_rare_resp"] = DialogNode(
            node_id="trade_rare_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("Ooh, you have an eye for quality! This amulet wards off "
                  "minor curses. One hundred gold. A bargain at twice the "
                  "price! I acquired it from a traveling sorcerer in dire "
                  "need of coin, if you must know."),
            mood=DialogMood.CURIOUS,
            tone=DialogTone.DIPLOMATIC,
            choices=[
                DialogChoice(choice_id="trade_rare_buy",
                             text="I'll take it.",
                             next_node="trade_buy_resp"),
                DialogChoice(choice_id="trade_rare_pass",
                             text="Out of my budget.",
                             next_node="trade_end"),
            ],
        )

        # Haggle
        tree.nodes["trade_haggle_resp"] = DialogNode(
            node_id="trade_haggle_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("You wound me! Very well, a small discount, for a valued "
                  "customer. But only because I like your face. Final price, "
                  "no further haggling!"),
            mood=DialogMood.SUSPICIOUS,
            tone=DialogTone.DIPLOMATIC,
            choices=[
                DialogChoice(choice_id="trade_haggle_done",
                             text="Done.",
                             next_node="trade_buy_resp"),
            ],
        )

        # Buy success
        tree.nodes["trade_buy_resp"] = DialogNode(
            node_id="trade_buy_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_merchant",
            text=("A pleasure doing business with you! Come again, Silas "
                  "always has new treasures! And do spread the word, word of "
                  "mouth is the lifeblood of commerce!"),
            mood=DialogMood.HAPPY,
            tone=DialogTone.DIPLOMATIC,
            actions=["set_flag:made_purchase",
                     "add_topic:trade"],
            choices=[
                DialogChoice(choice_id="trade_buy_end",
                             text="Will do. Farewell.",
                             next_node="trade_end"),
            ],
        )

        # End node
        tree.nodes["trade_end"] = DialogNode(
            node_id="trade_end",
            node_type=DialogNodeType.END,
            speaker_id="npc_merchant",
            text=("Safe travels, friend! May your purse stay heavy and your "
                  "sword stay sharp! The Emporium is always open for you!"),
            mood=DialogMood.HAPPY,
            tone=DialogTone.DIPLOMATIC,
        )

        self._trees[tree.tree_id] = tree

    def _seed_lore_tree(self) -> None:
        """Create the lore dialog tree for the mysterious stranger (11 nodes)."""
        tree = DialogTree(
            tree_id="tree_lore",
            name="The Hooded Wanderer's Lore",
            npc_id="npc_mysterious_stranger",
            root_node="lore_root",
            nodes={},
            start_mood=DialogMood.SUSPICIOUS,
            start_relationship=DialogRelationship.UNFRIENDLY,
            topics=[DialogTopic.LORE, DialogTopic.PERSONAL],
            metadata={"location": "unknown"},
        )

        # Root: The Wanderer speaks
        tree.nodes["lore_root"] = DialogNode(
            node_id="lore_root",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("...You. I have been waiting. Sit. There are things you "
                  "should know, whether you wish to or not. The threads of "
                  "fate weave strangely around you."),
            mood=DialogMood.SUSPICIOUS,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_identity",
                             text="Who are you?",
                             next_node="lore_identity_resp"),
                DialogChoice(choice_id="lore_prophecy",
                             text="Waiting for me?",
                             next_node="lore_prophecy_resp"),
            ],
        )

        # Identity
        tree.nodes["lore_identity_resp"] = DialogNode(
            node_id="lore_identity_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("Names are chains. I am what I have always been: a keeper "
                  "of truths others would rather forget. You may call me "
                  "what you wish. I will not answer to it regardless."),
            mood=DialogMood.SUSPICIOUS,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_truth",
                             text="What truths?",
                             next_node="lore_truth_resp"),
                DialogChoice(choice_id="lore_elusive",
                             text="That's vague.",
                             next_node="lore_elusive_resp"),
            ],
        )

        # Prophecy
        tree.nodes["lore_prophecy_resp"] = DialogNode(
            node_id="lore_prophecy_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("The old texts speak of one who walks between fate and "
                  "choice. Your steps echo in ways you cannot yet see. I am "
                  "here to show you the path, if you have the courage to "
                  "look."),
            mood=DialogMood.CURIOUS,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_defiance",
                             text="I make my own fate.",
                             next_node="lore_defiance_resp"),
                DialogChoice(choice_id="lore_more",
                             text="Tell me more.",
                             next_node="lore_truth_resp"),
            ],
        )

        # The truth about the Shards
        tree.nodes["lore_truth_resp"] = DialogNode(
            node_id="lore_truth_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("Long ago, the Shards of Aether were scattered to seal the "
                  "Rift. They are stirring once more. And so are the things "
                  "beneath. The world you know rests on a cracked foundation."),
            mood=DialogMood.FEARFUL,
            tone=DialogTone.MYSTERIOUS,
            actions=["set_flag:knows_shards",
                     "add_topic:lore"],
            choices=[
                DialogChoice(choice_id="lore_rift",
                             text="The Rift?",
                             next_node="lore_rift_resp"),
                DialogChoice(choice_id="lore_shards",
                             text="The Shards?",
                             next_node="lore_shards_resp"),
            ],
        )

        # Elusive
        tree.nodes["lore_elusive_resp"] = DialogNode(
            node_id="lore_elusive_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("Vague, perhaps. But precise where it matters. You will "
                  "understand, in time. If you survive long enough. Most do "
                  "not. I have watched many fall."),
            mood=DialogMood.SAD,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_elusive_truth",
                             text="Then tell me what matters.",
                             next_node="lore_truth_resp"),
            ],
        )

        # The Rift
        tree.nodes["lore_rift_resp"] = DialogNode(
            node_id="lore_rift_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("A wound in the world, where the Unspoken seep through. "
                  "It was closed, never healed. Now the stitches fray. When "
                  "it tears open, the age of light ends. Pray you are not "
                  "alive to see it. Or pray that you are the one who stops it."),
            mood=DialogMood.FEARFUL,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_rift_shards",
                             text="Can it be closed again?",
                             next_node="lore_shards_resp"),
            ],
        )

        # The Shards
        tree.nodes["lore_shards_resp"] = DialogNode(
            node_id="lore_shards_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("Seven fragments, seven guardians, seven trials. Seek them, "
                  "and you may yet turn the tide. Fail, and all is ash. The "
                  "first Shard lies where the sun forgets to shine. Do not "
                  "trust the silence there."),
            mood=DialogMood.CURIOUS,
            tone=DialogTone.MYSTERIOUS,
            actions=["set_flag:knows_shard_locations",
                     "set_flag:quest_shards"],
            choices=[
                DialogChoice(choice_id="lore_shards_accept",
                             text="I'll find them.",
                             next_node="lore_accept_resp"),
                DialogChoice(choice_id="lore_shards_doubt",
                             text="This is madness.",
                             next_node="lore_doubt_resp"),
            ],
        )

        # Defiance
        tree.nodes["lore_defiance_resp"] = DialogNode(
            node_id="lore_defiance_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("Defiance. Good. You will need it. Fate respects few "
                  "things, but it respects fire. Burn bright, and perhaps "
                  "you will not be consumed. Or perhaps you will. The "
                  "outcome is not yet written."),
            mood=DialogMood.TRUSTING,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_defiance_truth",
                             text="Then point me at the fire.",
                             next_node="lore_truth_resp"),
            ],
        )

        # Accept
        tree.nodes["lore_accept_resp"] = DialogNode(
            node_id="lore_accept_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("Then go. The first Shard lies where the sun forgets to "
                  "shine. Do not trust the silence there. And do not trust "
                  "anyone who claims to serve the light. Not all that glows "
                  "is gold, and not all that whispers is a friend."),
            mood=DialogMood.TRUSTING,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_accept_end",
                             text="I understand.",
                             next_node="lore_end"),
            ],
        )

        # Doubt
        tree.nodes["lore_doubt_resp"] = DialogNode(
            node_id="lore_doubt_resp",
            node_type=DialogNodeType.NPC_LINE,
            speaker_id="npc_mysterious_stranger",
            text=("Madness, perhaps. But madness and truth share a roof. "
                  "Sleep on it, if you can. The dreams will come. They "
                  "always do, for those touched by the Shards. I will be "
                  "here when you wake. If you wake."),
            mood=DialogMood.SAD,
            tone=DialogTone.MYSTERIOUS,
            choices=[
                DialogChoice(choice_id="lore_doubt_end",
                             text="...I'll think on it.",
                             next_node="lore_end"),
            ],
        )

        # End node
        tree.nodes["lore_end"] = DialogNode(
            node_id="lore_end",
            node_type=DialogNodeType.END,
            speaker_id="npc_mysterious_stranger",
            text=("Go, now. We will speak again, when the stars are right. "
                  "All will be revealed... in time."),
            mood=DialogMood.SUSPICIOUS,
            tone=DialogTone.MYSTERIOUS,
        )

        self._trees[tree.tree_id] = tree

    def _seed_sessions(self) -> None:
        """Create ten seed sessions across the four dialog trees."""
        # Map players to trees with varied states
        session_specs: List[Tuple[str, str, DialogStatus, DialogMood,
                                  DialogRelationship]] = [
            ("tree_greeting", "player_001", DialogStatus.ACTIVE,
             DialogMood.HAPPY, DialogRelationship.FRIENDLY),
            ("tree_greeting", "player_002", DialogStatus.ACTIVE,
             DialogMood.CURIOUS, DialogRelationship.NEUTRAL),
            ("tree_greeting", "player_003", DialogStatus.PAUSED,
             DialogMood.NEUTRAL, DialogRelationship.FRIENDLY),
            ("tree_quest", "player_001", DialogStatus.ACTIVE,
             DialogMood.NEUTRAL, DialogRelationship.NEUTRAL),
            ("tree_quest", "player_004", DialogStatus.ACTIVE,
             DialogMood.ANGRY, DialogRelationship.UNFRIENDLY),
            ("tree_quest", "player_005", DialogStatus.ENDED,
             DialogMood.HAPPY, DialogRelationship.FRIENDLY),
            ("tree_trade", "player_002", DialogStatus.ACTIVE,
             DialogMood.HAPPY, DialogRelationship.FRIENDLY),
            ("tree_trade", "player_006", DialogStatus.PAUSED,
             DialogMood.SUSPICIOUS, DialogRelationship.NEUTRAL),
            ("tree_lore", "player_001", DialogStatus.ACTIVE,
             DialogMood.SUSPICIOUS, DialogRelationship.UNFRIENDLY),
            ("tree_lore", "player_007", DialogStatus.ACTIVE,
             DialogMood.CURIOUS, DialogRelationship.NEUTRAL),
        ]

        for idx, (tree_id, player_id, status, mood, rel) in enumerate(
                session_specs):
            tree = self._trees.get(tree_id)
            if tree is None or not tree.root_node:
                continue
            session_id = f"seed_ses_{idx:02d}"
            session = DialogSession(
                session_id=session_id,
                tree_id=tree_id,
                player_id=player_id,
                current_node=tree.root_node,
                mood=mood,
                relationship=rel,
                sentiment=DialogSentiment.NEUTRAL,
                topics_discussed=[t.value for t in tree.topics[:1]],
                choices_made=[],
                started_at=_now_ts() - idx * 60,
                status=status,
                metadata={"seed": True, "last_activity": _now_ts() - idx * 30},
            )
            self._sessions[session_id] = session

    def _seed_events(self) -> None:
        """Create six seed events on the dialog timeline."""
        seed_event_specs: List[Tuple[DialogEventKind, str, str,
                                     Dict[str, Any]]] = [
            (DialogEventKind.STARTED,
             "Dialog director initialized",
             "",
             {"component": "ai_dialog_director"}),
            (DialogEventKind.STARTED,
             "Five NPC profiles seeded",
             "",
             {"count": 5}),
            (DialogEventKind.STARTED,
             "Four dialog trees seeded",
             "",
             {"count": 4, "trees": ["tree_greeting", "tree_quest",
                                    "tree_trade", "tree_lore"]}),
            (DialogEventKind.STARTED,
             "Ten seed sessions created",
             "",
             {"count": 10}),
            (DialogEventKind.MOOD_UPDATED,
             "Initial moods assigned to sessions",
             "seed_ses_00",
             {"mood": "happy"}),
            (DialogEventKind.RELATIONSHIP_UPDATED,
             "Initial relationships assigned to sessions",
             "seed_ses_04",
             {"relationship": "unfriendly"}),
        ]
        for kind, desc, sid, data in seed_event_specs:
            event = DialogEvent(
                event_id=_new_id("evt"),
                kind=kind,
                timestamp=_now_ts(),
                session_id=sid,
                description=desc,
                data=data,
            )
            self._events.append(event)


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_ai_dialog_director() -> AIDialogDirector:
    """Return the singleton AIDialogDirector instance."""
    return AIDialogDirector.get_instance()