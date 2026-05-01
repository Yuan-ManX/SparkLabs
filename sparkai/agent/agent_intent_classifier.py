"""
SparkAI Agent - Intent Classifier

Intent classification engine that routes user prompts to appropriate
agent workflows. Classifies game development prompts into structured
intents, enabling the agent system to select the right tools, models,
and execution strategies for each request type.

Architecture:
  IntentClassifier
    |-- KeywordMatcher (fast pre-filter using keyword patterns)
    |-- ContextAnalyzer (semantic analysis of prompt structure)
    |-- IntentRouter (maps intents to execution pipelines)
    |-- ConfidenceScorer (multi-signal confidence estimation)

Intent Categories:
  - WORLD: terrain, biomes, environment generation
  - CHARACTER: player, NPC, enemy creation
  - MECHANIC: game rules, systems, physics
  - NARRATIVE: story, dialogue, quest design
  - ASSET: textures, models, sounds
  - CODE: game scripts, engine code
  - ANALYSIS: review, debug, optimize existing content
  - ORCHESTRATE: multi-step pipelines combining above intents
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PromptIntent(Enum):
    WORLD = "world"
    CHARACTER = "character"
    NPC = "npc"
    ENEMY = "enemy"
    MECHANIC = "mechanic"
    NARRATIVE = "narrative"
    DIALOGUE = "dialogue"
    QUEST = "quest"
    ASSET = "asset"
    CODE = "code"
    ANALYSIS = "analysis"
    ORCHESTRATE = "orchestrate"
    GENERAL = "general"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    primary: PromptIntent = PromptIntent.UNKNOWN
    secondary: List[PromptIntent] = field(default_factory=list)
    confidence: float = 0.0
    keywords_matched: List[str] = field(default_factory=list)
    suggested_pipeline: str = ""
    entity_type: str = ""
    detail_level: str = "standard"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary.value,
            "secondary": [s.value for s in self.secondary],
            "confidence": round(self.confidence, 3),
            "keywords_matched": self.keywords_matched,
            "suggested_pipeline": self.suggested_pipeline,
            "entity_type": self.entity_type,
            "detail_level": self.detail_level,
        }

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.6


INTENT_PATTERNS: Dict[PromptIntent, List[Tuple[str, float]]] = {
    PromptIntent.WORLD: [
        (r"\b(terrain|landscape|biome|environment|world|map|level|ocean|forest|desert|mountain|island|planet|dungeon)\b", 0.15),
        (r"\b(generate|create|build|design|make)\b.*\b(world|terrain|environment|map|level|landscape|realm)\b", 0.20),
        (r"\b(procedural|random|seed)\b.*\b(generat|terrain|world)\b", 0.25),
        (r"\b(open.world|sandbox|explorable)\b", 0.15),
    ],
    PromptIntent.CHARACTER: [
        (r"\b(character|player|hero|protagonist|avatar|persona)\b", 0.15),
        (r"\b(generate|create|design|make|build)\b.*\b(character|player|hero|protagonist)\b", 0.20),
        (r"\b(backstory|personality|trait|skill|ability|class|race)\b", 0.10),
    ],
    PromptIntent.NPC: [
        (r"\b(npc|non.player|vendor|merchant|quest.giver|villager|townsfolk)\b", 0.15),
        (r"\b(create|generate|spawn|place)\b.*\b(npc|character)\b", 0.15),
        (r"\b(dialog|conversation|speak|talk|interact)\b.*\b(npc|character)\b", 0.10),
    ],
    PromptIntent.ENEMY: [
        (r"\b(enemy|monster|boss|creature|beast|dragon|zombie|undead|goblin|orc)\b", 0.15),
        (r"\b(combat|fight|battle|attack|damage|health|hp|ai.behavio)\b", 0.10),
        (r"\b(spawn|generate)\b.*\b(enemy|monster|mob)\b", 0.20),
    ],
    PromptIntent.MECHANIC: [
        (r"\b(mechanic|gameplay|system|rule|physics|inventory|crafting|combat.system|economy)\b", 0.15),
        (r"\b(design|implement|add|create)\b.*\b(system|mechanic|rule|physics)\b", 0.15),
        (r"\b(balance|tuning|difficulty|progression|leveling|skill.tree)\b", 0.10),
    ],
    PromptIntent.NARRATIVE: [
        (r"\b(story|plot|narrative|lore|backstory|history|timeline|arc|chapter)\b", 0.15),
        (r"\b(write|generate|create|tell|craft)\b.*\b(story|narrative|plot|lore)\b", 0.15),
        (r"\b(world.building|setting|universe|mythology|legend)\b", 0.10),
    ],
    PromptIntent.DIALOGUE: [
        (r"\b(dialog|conversation|speak|talk|chat|greet|respond|say)\b", 0.15),
        (r"\b(dialog.tree|branching|choice|option|response)\b", 0.20),
        (r"\b(write|generate)\b.*\b(dialog|conversation|script)\b", 0.15),
    ],
    PromptIntent.QUEST: [
        (r"\b(quest|mission|task|objective|goal|side.quest|main.quest|fetch|escort)\b", 0.15),
        (r"\b(design|create|generate)\b.*\b(quest|mission)\b", 0.15),
        (r"\b(reward|loot|treasure|xp|experience)\b", 0.05),
    ],
    PromptIntent.ASSET: [
        (r"\b(texture|model|mesh|sprite|animation|sound|music|audio|vfx|particle|shader|material)\b", 0.15),
        (r"\b(generate|create|import|export)\b.*\b(asset|texture|model|sound|animation)\b", 0.15),
        (r"\b(2d|3d|pixel.art|voxel|low.poly)\b", 0.10),
    ],
    PromptIntent.CODE: [
        (r"\b(code|script|program|function|class|api|sdk|framework|engine)\b", 0.10),
        (r"\b(write|generate|implement|fix|debug|refactor)\b.*\b(code|script|function)\b", 0.15),
        (r"\b(python|javascript|lua|csharp|c\+\+|typescript|rust)\b", 0.10),
        (r"\b(module|package|library|plugin|extension|addon)\b", 0.05),
    ],
    PromptIntent.ANALYSIS: [
        (r"\b(analyze|review|check|audit|inspect|examine|evaluate|assess)\b", 0.15),
        (r"\b(bug|issue|error|problem|broken|fix|debug|optimize|improve|enhance)\b", 0.10),
        (r"\b(performance|fps|lag|slow|bottleneck|memory|leak)\b", 0.10),
    ],
    PromptIntent.ORCHESTRATE: [
        (r"\b(full.game|complete.project|entire|whole|everything|all.in.one)\b", 0.20),
        (r"\b(pipeline|workflow|orchestrat|multi.step|end.to.end)\b", 0.20),
        (r"\b(build|make|create|develop)\b.*\b(game|project|world|experience)\b", 0.15),
    ],
}


def _strip_punctuation(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


class IntentClassifier:
    """
    Multi-strategy intent classification engine.

    Classifies game development prompts using layered analysis:
    1. Fast keyword matching for primary intent detection
    2. Pattern-based scoring with weighted confidence
    3. Secondary intent detection for compound prompts
    4. Pipeline suggestion based on intent cluster

    Usage:
        classifier = IntentClassifier()
        result = classifier.classify("Create a fantasy world with forests and mountains")
        print(result.primary)  # PromptIntent.WORLD
    """

    def __init__(self):
        self._compiled: Dict[PromptIntent, List[Tuple[re.Pattern, float]]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        for intent, patterns in INTENT_PATTERNS.items():
            compiled = []
            for pattern_str, weight in patterns:
                compiled.append((re.compile(pattern_str, re.IGNORECASE), weight))
            self._compiled[intent] = compiled

    def classify(self, prompt: str) -> IntentResult:
        if not prompt or not prompt.strip():
            return IntentResult()

        normalized = _strip_punctuation(prompt)

        scores: Dict[PromptIntent, Tuple[float, List[str]]] = {}
        for intent, patterns in self._compiled.items():
            total = 0.0
            matched_keywords: List[str] = []
            for pattern, weight in patterns:
                matches = pattern.findall(normalized)
                if matches:
                    total += weight
                    matched_keywords.append(pattern.pattern[:40])

            if total > 0:
                scores[intent] = (total, matched_keywords)

        if not scores:
            return IntentResult(
                primary=PromptIntent.GENERAL,
                confidence=0.3,
                detail_level="standard",
            )

        sorted_scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)

        primary_intent, (primary_score, primary_keywords) = sorted_scores[0]
        confidence = min(primary_score * 1.5, 1.0)

        secondary = []
        for intent, (score, _) in sorted_scores[1:3]:
            if score >= 0.1:
                secondary.append(intent)

        pipeline = self._suggest_pipeline(primary_intent, secondary)
        entity_type = self._infer_entity_type(primary_intent, prompt)
        detail_level = self._infer_detail_level(prompt)

        return IntentResult(
            primary=primary_intent,
            secondary=secondary,
            confidence=confidence,
            keywords_matched=primary_keywords,
            suggested_pipeline=pipeline,
            entity_type=entity_type,
            detail_level=detail_level,
        )

    def _suggest_pipeline(self, primary: PromptIntent, secondary: List[PromptIntent]) -> str:
        all_intents = [primary] + secondary

        has_world = PromptIntent.WORLD in all_intents
        has_char = PromptIntent.CHARACTER in all_intents or PromptIntent.NPC in all_intents
        has_narrative = PromptIntent.NARRATIVE in all_intents or PromptIntent.DIALOGUE in all_intents
        has_mechanic = PromptIntent.MECHANIC in all_intents
        has_asset = PromptIntent.ASSET in all_intents

        if PromptIntent.ORCHESTRATE in all_intents:
            return "full_game_generation"
        if has_world and has_char:
            return "world_with_entities"
        if has_world:
            return "world_generation"
        if has_char:
            return "entity_creation"
        if has_narrative:
            return "narrative_design"
        if has_mechanic:
            return "mechanic_implementation"
        if has_asset:
            return "asset_generation"
        if PromptIntent.CODE in all_intents:
            return "code_execution"
        if PromptIntent.ANALYSIS in all_intents:
            return "analysis_review"

        return "standard_agent_loop"

    def _infer_entity_type(self, primary: PromptIntent, prompt: str) -> str:
        entity_map = {
            PromptIntent.WORLD: "world",
            PromptIntent.CHARACTER: "character",
            PromptIntent.NPC: "npc",
            PromptIntent.ENEMY: "enemy",
            PromptIntent.MECHANIC: "mechanic",
            PromptIntent.NARRATIVE: "narrative",
            PromptIntent.DIALOGUE: "dialogue",
            PromptIntent.QUEST: "quest",
            PromptIntent.ASSET: "asset",
            PromptIntent.CODE: "code",
        }
        return entity_map.get(primary, "entity")

    def _infer_detail_level(self, prompt: str) -> str:
        words = prompt.lower().split()
        if any(w in words for w in ["detailed", "rich", "complex", "elaborate", "deep", "comprehensive"]):
            return "high"
        if any(w in words for w in ["quick", "simple", "basic", "minimal", "rough", "sketch"]):
            return "low"
        return "standard"

    def classify_batch(self, prompts: List[str]) -> List[IntentResult]:
        return [self.classify(p) for p in prompts]

    def get_intent_summary(self, results: List[IntentResult]) -> Dict[str, Any]:
        if not results:
            return {}

        confident_results = [r for r in results if r.is_confident]
        primary_counts: Dict[str, int] = {}
        for r in confident_results:
            key = r.primary.value
            primary_counts[key] = primary_counts.get(key, 0) + 1

        return {
            "total_prompts": len(results),
            "confident_classifications": len(confident_results),
            "primary_intents": primary_counts,
            "top_intent": max(primary_counts, key=primary_counts.get) if primary_counts else "unknown",
        }


_global_intent_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    global _global_intent_classifier
    if _global_intent_classifier is None:
        _global_intent_classifier = IntentClassifier()
    return _global_intent_classifier
