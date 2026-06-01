"""
SparkLabs Agent - Game Design Intelligence

A comprehensive game design intelligence system that analyzes game mechanics,
brainstorms creative design variations, predicts systemic balance, and explores
the full game design space through structured reasoning and iteration.

Architecture:
  GameDesignIntelligence (singleton)
    |-- DesignConcept (creative game design idea with mechanics and themes)
    |-- DesignSession (interactive design exploration session)
    |-- MechanicAnalysis (deep analysis of a single game mechanic)
    |-- BalancePrediction (predicted balance outcome for systemic interactions)
    |-- DesignDomain (game design knowledge domains)
    |-- DesignPhase (creative process phases)

Core Capabilities:
  - brainstorm_mechanics: Generate creative mechanic variations from seed concepts
  - analyze_mechanic: Deep analysis of mechanic depth, synergies, and edge cases
  - predict_balance: Forecast systemic balance from mechanic interactions
  - explore_design_space: Systematic exploration of combinatorial design possibilities
  - evaluate_fun_factor: Score game concepts across engagement dimensions
  - iterate_concept: Generate improved iterations of a design concept
  - generate_pitch: Create complete game design documents from concepts
  - compare_concepts: Side-by-side analysis of competing design approaches
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Set

_time_module = time


class DesignDomain(Enum):
    CORE_LOOP = "core_loop"
    PROGRESSION = "progression"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    ECONOMY = "economy"
    NARRATIVE = "narrative"
    SOCIAL = "social"
    PUZZLE = "puzzle"
    PLATFORMING = "platforming"
    STRATEGY = "strategy"
    SIMULATION = "simulation"
    RHYTHM = "rhythm"
    STEALTH = "stealth"
    SURVIVAL = "survival"
    CRAFTING = "crafting"


class DesignPhase(Enum):
    IDEATION = "ideation"
    CONCEPTUALIZATION = "conceptualization"
    REFINEMENT = "refinement"
    BALANCING = "balancing"
    PROTOTYPING = "prototyping"
    POLISHING = "polishing"


class MechanicCategory(Enum):
    MOVEMENT = "movement"
    INTERACTION = "interaction"
    RESOURCE = "resource"
    CONFLICT = "conflict"
    GROWTH = "growth"
    CONSTRAINT = "constraint"
    FEEDBACK = "feedback"
    EMERGENCE = "emergence"


class EngagementDimension(Enum):
    CHALLENGE = "challenge"
    CURIOSITY = "curiosity"
    MASTERY = "mastery"
    AGENCY = "agency"
    SURPRISE = "surprise"
    FLOW = "flow"
    SOCIAL_BONDING = "social_bonding"
    NARRATIVE_IMMERSION = "narrative_immersion"
    AESTHETIC_APPEAL = "aesthetic_appeal"
    CREATIVE_EXPRESSION = "creative_expression"


class BalanceDimension(Enum):
    POWER_CURVE = "power_curve"
    RESOURCE_ECONOMY = "resource_economy"
    RISK_REWARD = "risk_reward"
    TIME_INVESTMENT = "time_investment"
    SKILL_CEILING = "skill_ceiling"
    ACCESSIBILITY = "accessibility"
    VARIETY_DEPTH = "variety_depth"
    SNOWBALL_RISK = "snowball_risk"
    COUNTERPLAY = "counterplay"
    PACING = "pacing"


class ConfidenceLevel(Enum):
    SPECULATIVE = "speculative"
    REASONABLE = "reasonable"
    CONFIDENT = "confident"
    VALIDATED = "validated"


@dataclass
class DesignConcept:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    genre: str = "action"
    core_mechanic: str = ""
    secondary_mechanics: List[str] = field(default_factory=list)
    theme: str = ""
    target_audience: str = ""
    unique_selling_point: str = ""
    complexity_score: float = 0.0
    innovation_score: float = 0.0
    feasibility_score: float = 0.0
    fun_factor: float = 0.0
    engagement_profile: Dict[str, float] = field(default_factory=dict)
    mechanic_tags: List[str] = field(default_factory=list)
    design_notes: List[str] = field(default_factory=list)
    iteration_count: int = 0
    phase: str = DesignPhase.IDEATION.value
    domain: str = DesignDomain.CORE_LOOP.value
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre,
            "core_mechanic": self.core_mechanic,
            "secondary_mechanics": self.secondary_mechanics,
            "theme": self.theme,
            "target_audience": self.target_audience,
            "unique_selling_point": self.unique_selling_point,
            "complexity_score": self.complexity_score,
            "innovation_score": self.innovation_score,
            "feasibility_score": self.feasibility_score,
            "fun_factor": self.fun_factor,
            "engagement_profile": self.engagement_profile,
            "mechanic_tags": self.mechanic_tags,
            "design_notes": self.design_notes,
            "iteration_count": self.iteration_count,
            "phase": self.phase,
            "domain": self.domain,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class MechanicAnalysis:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mechanic_name: str = ""
    category: str = MechanicCategory.INTERACTION.value
    depth_score: float = 0.0
    synergy_potential: float = 0.0
    edge_cases: List[str] = field(default_factory=list)
    known_patterns: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    variation_ideas: List[str] = field(default_factory=list)
    player_skill_dependency: float = 0.0
    accessibility_issues: List[str] = field(default_factory=list)
    complexity_contribution: float = 0.0
    balance_impact: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mechanic_name": self.mechanic_name,
            "category": self.category,
            "depth_score": self.depth_score,
            "synergy_potential": self.synergy_potential,
            "edge_cases": self.edge_cases,
            "known_patterns": self.known_patterns,
            "risk_factors": self.risk_factors,
            "variation_ideas": self.variation_ideas,
            "player_skill_dependency": self.player_skill_dependency,
            "accessibility_issues": self.accessibility_issues,
            "complexity_contribution": self.complexity_contribution,
            "balance_impact": self.balance_impact,
            "recommendation": self.recommendation,
        }


@dataclass
class BalancePrediction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    system_name: str = ""
    dimensions: Dict[str, float] = field(default_factory=dict)
    confidence: str = ConfidenceLevel.SPECULATIVE.value
    dominant_strategies: List[str] = field(default_factory=list)
    underpowered_elements: List[str] = field(default_factory=list)
    overpowered_elements: List[str] = field(default_factory=list)
    pivot_recommendations: List[str] = field(default_factory=list)
    tuning_parameters: Dict[str, Any] = field(default_factory=dict)
    equilibrium_point: Optional[float] = None
    volatility_index: float = 0.0
    design_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "system_name": self.system_name,
            "dimensions": self.dimensions,
            "confidence": self.confidence,
            "dominant_strategies": self.dominant_strategies,
            "underpowered_elements": self.underpowered_elements,
            "overpowered_elements": self.overpowered_elements,
            "pivot_recommendations": self.pivot_recommendations,
            "tuning_parameters": self.tuning_parameters,
            "equilibrium_point": self.equilibrium_point,
            "volatility_index": self.volatility_index,
            "design_notes": self.design_notes,
        }


@dataclass
class DesignSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    topic: str = ""
    domain: str = DesignDomain.CORE_LOOP.value
    concepts: List[str] = field(default_factory=list)
    active_concept_id: Optional[str] = None
    analyses: List[str] = field(default_factory=list)
    predictions: List[str] = field(default_factory=list)
    phase: str = DesignPhase.IDEATION.value
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "domain": self.domain,
            "concepts": self.concepts,
            "active_concept_id": self.active_concept_id,
            "analyses": self.analyses,
            "predictions": self.predictions,
            "phase": self.phase,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


_MECHANIC_KNOWLEDGE_BASE: Dict[str, List[str]] = {
    "double_jump": ["aerial movement", "traversal", "obstacle avoidance", "combo accessibility"],
    "dash_ability": ["mobility burst", "dodge mechanic", "gap crossing", "speed modifier"],
    "grappling_hook": ["momentum physics", "vertical mobility", "attachment points", "swing arc"],
    "time_manipulation": ["temporal puzzle", "rewind mechanic", "slow_field", "paradox"],
    "elemental_system": ["type advantage", "status effects", "environment interaction", "counter"],
    "crafting_system": ["resource loop", "recipe discovery", "equipment progression", "economy"],
    "procedural_generation": ["replayability", "seed control", "difficulty scaling", "content variety"],
    "morality_system": ["choice consequence", "narrative branching", "reputation tracking", "alignment"],
    "skill_tree": ["character progression", "build diversity", "respec options", "synergy bonuses"],
    "stealth_system": ["visibility cone", "sound radius", "distraction tools", "detection states"],
    "base_building": ["spatial planning", "resource management", "defense layout", "automation"],
    "faction_system": ["relationship network", "diplomacy options", "reputation thresholds", "betrayal"],
    "weather_system": ["environmental hazards", "visibility impact", "movement modifier", "atmosphere"],
    "day_night_cycle": ["time pressure", "enemy behavior shift", "visual mood", "schedule systems"],
    "dialogue_tree": ["branching conversation", "skill checks", "relationship impact", "information gate"],
}


_GENRE_MECHANIC_MATRIX: Dict[str, List[str]] = {
    "platformer": ["jump_physics", "moving_platforms", "hazard_patterns", "collectibles", "checkpoints"],
    "rpg": ["stats_growth", "inventory", "quest_log", "party_system", "equipment_slots"],
    "strategy": ["grid_based", "resource_income", "tech_tree", "fog_of_war", "unit_types"],
    "shooter": ["projectile_physics", "cover_system", "ammo_management", "hit_scan", "recoil"],
    "puzzle": ["rule_discovery", "constraint_chain", "hint_system", "reset_mechanic", "solution_path"],
    "roguelike": ["permadeath", "random_generation", "metaprogression", "item_synergy", "seed_run"],
    "racing": ["acceleration_curve", "drift_mechanic", "boost_system", "track_variants", "lap_timing"],
    "simulation": ["emergent_behavior", "agent_ai", "resource_chain", "environment_modification", "tick_system"],
    "fighting": ["combo_system", "frame_data", "hit_confirm", "meter_management", "matchup_knowledge"],
    "survival": ["hunger_system", "crafting_tree", "base_defense", "resource_scarcity", "threat_escalation"],
    "metroidvania": ["ability_gate", "map_reveal", "sequence_break", "backtracking", "upgrade_stack"],
    "sandbox": ["physics_toy", "player_goal", "emergent_narrative", "world_simulation", "creative_mode"],
}


_DESIGN_PATTERNS: Dict[str, Dict[str, Any]] = {
    "easy_to_learn_hard_to_master": {
        "description": "Simple core with deep skill expression",
        "key_mechanics": ["low_entry_barrier", "high_skill_ceiling", "obvious_feedback", "hidden_depth"],
        "risk_factors": ["frustrating_for_beginners", "plateau_at_intermediate"],
        "engagement_boost": ["mastery", "challenge", "flow"],
    },
    "emergent_gameplay": {
        "description": "Simple rules creating complex outcomes",
        "key_mechanics": ["systemic_interactions", "player_agency", "unpredictable_outcomes"],
        "risk_factors": ["unbalanced_emergence", "player_confusion", "unintended_strategies"],
        "engagement_boost": ["surprise", "curiosity", "creative_expression"],
    },
    "risk_reward_loop": {
        "description": "Push-your-luck mechanics with escalating stakes",
        "key_mechanics": ["stakes_escalation", "exit_decision", "information_asymmetry", "loss_aversion"],
        "risk_factors": ["frustration_spikes", "optimal_strategy_collapse"],
        "engagement_boost": ["challenge", "agency", "curiosity"],
    },
    "discovery_driven": {
        "description": "Player motivation through exploration and revelation",
        "key_mechanics": ["fog_of_war", "hidden_content", "breadcrumb_trail", "aha_moments"],
        "risk_factors": ["content_exhaustion", "frustrating_obscurity", "guide_dependency"],
        "engagement_boost": ["curiosity", "surprise", "narrative_immersion"],
    },
    "social_expression": {
        "description": "Self-expression through customization and sharing",
        "key_mechanics": ["cosmetic_system", "build_sharing", "player_housing", "leaderboard_identity"],
        "risk_factors": ["monetization_backlash", "toxic_comparison", "content_moderation"],
        "engagement_boost": ["social_bonding", "creative_expression", "aesthetic_appeal"],
    },
}


class GameDesignIntelligence:
    _instance: Optional[GameDesignIntelligence] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> GameDesignIntelligence:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> GameDesignIntelligence:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._concepts: Dict[str, DesignConcept] = {}
        self._analyses: Dict[str, MechanicAnalysis] = {}
        self._predictions: Dict[str, BalancePrediction] = {}
        self._sessions: Dict[str, DesignSession] = {}
        self._active_session_id: Optional[str] = None

        self._total_concepts: int = 0
        self._total_analyses: int = 0
        self._total_predictions: int = 0
        self._total_sessions: int = 0
        self._total_brainstorms: int = 0

    def start_session(self, topic: str, domain: str = DesignDomain.CORE_LOOP.value) -> DesignSession:
        session = DesignSession(
            topic=topic,
            domain=domain,
            metadata={"start_method": "api"},
        )
        self._sessions[session.id] = session
        self._active_session_id = session.id
        self._total_sessions += 1
        return session

    def brainstorm_mechanics(
        self,
        seed_concept: str,
        genre: str = "action",
        count: int = 5,
        innovation_level: float = 0.7,
    ) -> List[DesignConcept]:
        concepts = []
        seed_lower = seed_concept.lower()
        genre_mechanics = _GENRE_MECHANIC_MATRIX.get(genre, _GENRE_MECHANIC_MATRIX["platformer"])

        base_mechanics = list(_MECHANIC_KNOWLEDGE_BASE.keys())
        scored_mechanics: List[Tuple[str, float]] = []
        for mechanic_name in base_mechanics:
            knowledge = _MECHANIC_KNOWLEDGE_BASE[mechanic_name]
            relevance = sum(1 for kw in knowledge if kw.replace("_", " ") in seed_lower or kw in seed_lower)
            similarity = 0.0
            for word in seed_lower.split():
                if word in mechanic_name or any(word in kw for kw in knowledge):
                    similarity += 0.3
            score = relevance * 0.5 + similarity * 0.3 + innovation_level * 0.2
            scored_mechanics.append((mechanic_name, score))

        scored_mechanics.sort(key=lambda x: x[1], reverse=True)
        selected = scored_mechanics[:count]

        for i, (mech_name, score) in enumerate(selected):
            knowledge = _MECHANIC_KNOWLEDGE_BASE[mech_name]
            concept = DesignConcept(
                title=f"{genre.title()} Concept: {mech_name.replace('_', ' ').title()}",
                genre=genre,
                core_mechanic=mech_name,
                secondary_mechanics=genre_mechanics[:3],
                mechanic_tags=knowledge,
                innovation_score=innovation_level * (1 + 0.2 * (len(selected) - i) / len(selected)),
                complexity_score=0.4 + 0.3 * (len(knowledge) / 10),
                feasibility_score=0.6 + 0.3 * (1 - innovation_level),
                fun_factor=min(1.0, 0.5 + score),
                engagement_profile={
                    dim.value: 0.3 + 0.7 * (score + (i % 3) * 0.1)
                    for dim in EngagementDimension
                },
                design_notes=[
                    f"Primary knowledge area: {knowledge[0]}",
                    f"Genre synergy: {genre} compatible",
                    f"Complexity depth: {len(knowledge)} knowledge tags",
                ],
                iteration_count=0,
            )
            concepts.append(concept)
            self._concepts[concept.id] = concept
            self._total_concepts += 1

        self._total_brainstorms += 1

        if self._active_session_id and self._active_session_id in self._sessions:
            session = self._sessions[self._active_session_id]
            session.concepts.extend([c.id for c in concepts])
            session.updated_at = _time_module.time()

        return concepts

    def analyze_mechanic(self, mechanic_name: str, context: Optional[Dict[str, Any]] = None) -> MechanicAnalysis:
        context = context or {}
        knowledge = _MECHANIC_KNOWLEDGE_BASE.get(mechanic_name, ["custom", mechanic_name])

        category = MechanicCategory.INTERACTION.value
        category_keywords = {
            MechanicCategory.MOVEMENT.value: ["movement", "speed", "jump", "dash", "traversal"],
            MechanicCategory.RESOURCE.value: ["resource", "economy", "crafting", "currency", "material"],
            MechanicCategory.CONFLICT.value: ["combat", "damage", "attack", "defense", "conflict"],
            MechanicCategory.GROWTH.value: ["progression", "skill", "upgrade", "tree", "level"],
            MechanicCategory.EMERGENCE.value: ["procedural", "generation", "emergent", "systemic", "simulation"],
        }
        for cat, keywords in category_keywords.items():
            if any(kw in mechanic_name or kw in " ".join(knowledge) for kw in keywords):
                category = cat
                break

        depth = min(1.0, 0.3 + len(knowledge) * 0.07)
        synergy = min(1.0, 0.4 + len(context.get("related_mechanics", [])) * 0.15)

        edge_cases = []
        if "physics" in " ".join(knowledge):
            edge_cases.append("Edge case: extreme velocity states may break collision detection")
        if "progression" in " ".join(knowledge):
            edge_cases.append("Edge case: max-level cap creates diminishing returns")
        if "resource" in " ".join(knowledge):
            edge_cases.append("Edge case: resource overflow may bypass intended scarcity")

        variation_ideas = []
        base_variations = {
            mechanic_name: [
                f"Invert the {mechanic_name}: replace positive with negative application",
                f"Time-gate the {mechanic_name}: add cooldown or charge mechanic",
                f"Chain the {mechanic_name}: allow sequential combinations with other mechanics",
            ]
        }
        variation_ideas = base_variations.get(mechanic_name, [
            f"Vary the {mechanic_name} intensity dynamically",
            f"Combine {mechanic_name} with a secondary modifier",
            f"Toggle {mechanic_name} between active and passive modes",
        ])

        analysis = MechanicAnalysis(
            mechanic_name=mechanic_name,
            category=category,
            depth_score=depth,
            synergy_potential=synergy,
            edge_cases=edge_cases,
            known_patterns=knowledge,
            risk_factors=[
                "Complexity budget overrun" if depth > 0.7 else "May feel shallow",
                "Balancing difficulty with high synergy" if synergy > 0.6 else "Low interaction potential",
            ],
            variation_ideas=variation_ideas,
            player_skill_dependency=0.3 + depth * 0.4,
            accessibility_issues=[
                "Requires precise input timing" if "movement" in category else "",
                "May require tutorialization for new players" if depth > 0.6 else "",
            ],
            complexity_contribution=depth * 0.6,
            balance_impact={
                dim.value: 0.3 + 0.5 * (depth * synergy)
                for dim in BalanceDimension
            },
            recommendation=(
                "High potential: integrate with progression system"
                if depth > 0.5 and synergy > 0.5
                else "Moderate: consider simplifying or adding more interaction points"
            ),
        )

        self._analyses[analysis.id] = analysis
        self._total_analyses += 1

        if self._active_session_id and self._active_session_id in self._sessions:
            self._sessions[self._active_session_id].analyses.append(analysis.id)

        return analysis

    def predict_balance(
        self,
        system_name: str,
        mechanic_ids: List[str],
        tuning_values: Optional[Dict[str, Any]] = None,
    ) -> BalancePrediction:
        tuning_values = tuning_values or {}
        mechanics_data: List[MechanicAnalysis] = []
        for mid in mechanic_ids:
            if mid in self._analyses:
                mechanics_data.append(self._analyses[mid])
            elif mid in self._concepts:
                concept = self._concepts[mid]
                analysis = self.analyze_mechanic(concept.core_mechanic)
                mechanics_data.append(analysis)

        avg_depth = sum(m.depth_score for m in mechanics_data) / max(len(mechanics_data), 1)
        avg_synergy = sum(m.synergy_potential for m in mechanics_data) / max(len(mechanics_data), 1)

        dominant_strategies = []
        if avg_synergy > 0.6:
            dominant_strategies.append("Synergy stacking: combining complementary mechanics")
        if avg_depth > 0.7:
            dominant_strategies.append("Depth exploitation: mastery of complex interactions")
        if len(mechanics_data) <= 2:
            dominant_strategies.append("Speed optimization: minimal interaction path")

        prediction = BalancePrediction(
            system_name=system_name,
            dimensions={
                dim.value: 0.3 + 0.5 * (avg_depth + avg_synergy) / 2
                for dim in BalanceDimension
            },
            confidence=(
                ConfidenceLevel.REASONABLE.value
                if len(mechanics_data) >= 3
                else ConfidenceLevel.SPECULATIVE.value
            ),
            dominant_strategies=dominant_strategies,
            underpowered_elements=[
                m.mechanic_name for m in mechanics_data if m.depth_score < 0.4
            ],
            overpowered_elements=[
                m.mechanic_name for m in mechanics_data if m.depth_score > 0.8 and m.synergy_potential > 0.7
            ],
            pivot_recommendations=[
                "Add counterplay options for dominant strategy",
                "Reduce synergy ceiling by introducing diminishing returns",
                "Introduce opportunity cost for stacking mechanics",
            ],
            tuning_parameters={
                "recommended_scale_factor": round(1.0 - 0.2 * avg_synergy, 2),
                "diminishing_threshold": round(0.6 + 0.2 * avg_depth, 2),
                "interaction_cap": max(3, int(len(mechanics_data) * 1.5)),
            },
            equilibrium_point=round(0.5 + 0.2 * avg_depth - 0.1 * avg_synergy, 2),
            volatility_index=round(0.3 + 0.5 * avg_synergy, 2),
        )

        self._predictions[prediction.id] = prediction
        self._total_predictions += 1

        if self._active_session_id and self._active_session_id in self._sessions:
            self._sessions[self._active_session_id].predictions.append(prediction.id)

        return prediction

    def evaluate_fun_factor(self, concept_id: str) -> Dict[str, Any]:
        concept = self._concepts.get(concept_id)
        if not concept:
            return {"error": f"Concept '{concept_id}' not found"}

        mechanic_weight = 0.0
        if concept.core_mechanic in _MECHANIC_KNOWLEDGE_BASE:
            mechanic_weight = len(_MECHANIC_KNOWLEDGE_BASE[concept.core_mechanic]) / 10.0

        engagement_scores = {}
        for dim in EngagementDimension:
            base = concept.engagement_profile.get(dim.value, 0.5)
            boosted = min(1.0, base * (1.0 + 0.2 * mechanic_weight))
            engagement_scores[dim.value] = round(boosted, 3)

        fun_factor = sum(engagement_scores.values()) / len(engagement_scores)

        design_pattern_matches = []
        for pattern_name, pattern_data in _DESIGN_PATTERNS.items():
            match_count = sum(
                1 for kw in pattern_data["key_mechanics"]
                if kw in " ".join(concept.mechanic_tags).lower()
            )
            if match_count >= 2:
                design_pattern_matches.append(pattern_name)

        concept.fun_factor = fun_factor
        concept.engagement_profile = engagement_scores
        concept.updated_at = _time_module.time()

        return {
            "concept_id": concept_id,
            "title": concept.title,
            "fun_factor": fun_factor,
            "engagement_scores": engagement_scores,
            "design_patterns_matched": design_pattern_matches,
            "mechanic_weight": mechanic_weight,
            "recommendation": (
                "Strong engagement potential across multiple dimensions"
                if fun_factor > 0.7
                else "Consider deepening mechanic interactions for higher engagement"
                if fun_factor > 0.5
                else "Revisit core loop to increase player engagement"
            ),
        }

    def iterate_concept(
        self,
        concept_id: str,
        iteration_direction: str = "deepen",
        iteration_count: int = 1,
    ) -> DesignConcept:
        concept = self._concepts.get(concept_id)
        if not concept:
            raise ValueError(f"Concept '{concept_id}' not found")

        for _ in range(iteration_count):
            if iteration_direction == "deepen":
                concept.complexity_score = min(1.0, concept.complexity_score + 0.15)
                concept.innovation_score = min(1.0, concept.innovation_score + 0.05)
                concept.secondary_mechanics.append(
                    _MECHANIC_KNOWLEDGE_BASE.get(concept.core_mechanic, ["depth_layer"])[0]
                )
            elif iteration_direction == "simplify":
                concept.complexity_score = max(0.1, concept.complexity_score - 0.15)
                concept.feasibility_score = min(1.0, concept.feasibility_score + 0.1)
                if len(concept.secondary_mechanics) > 1:
                    concept.secondary_mechanics.pop()
            elif iteration_direction == "innovate":
                concept.innovation_score = min(1.0, concept.innovation_score + 0.2)
                pattern = list(_DESIGN_PATTERNS.keys())[
                    hash(concept_id + str(concept.iteration_count)) % len(_DESIGN_PATTERNS)
                ]
                concept.design_notes.append(f"Innovation pass: applying {pattern} pattern")
            elif iteration_direction == "balance":
                concept.fun_factor = min(1.0, concept.fun_factor + 0.08)
                concept.mechanic_tags.append("balanced")
                concept.design_notes.append("Balance pass: smoothed power curve and resource economy")

            concept.iteration_count += 1
            concept.phase = DesignPhase.REFINEMENT.value
            concept.updated_at = _time_module.time()

        return concept

    def explore_design_space(
        self,
        base_concept_id: str,
        dimensions: Optional[List[str]] = None,
        variation_count: int = 4,
    ) -> List[DesignConcept]:
        base = self._concepts.get(base_concept_id)
        if not base:
            return []

        dimensions = dimensions or ["complexity", "innovation", "accessibility"]
        variations = []

        for i in range(variation_count):
            variant = DesignConcept(
                title=f"{base.title} (Variant {i + 1})",
                genre=base.genre,
                core_mechanic=base.core_mechanic,
                secondary_mechanics=list(base.secondary_mechanics),
                mechanic_tags=list(base.mechanic_tags),
                complexity_score=max(0.1, min(1.0, base.complexity_score + (i - 1) * 0.2)),
                innovation_score=max(0.1, min(1.0, base.innovation_score + ((i % 2) * 2 - 1) * 0.15)),
                feasibility_score=max(0.1, min(1.0, base.feasibility_score - 0.05 * i)),
                fun_factor=base.fun_factor,
                engagement_profile={
                    dim: base.engagement_profile.get(dim, 0.5) + ((i - 1) * 0.08)
                    for dim in base.engagement_profile
                },
                design_notes=[
                    f"Design space variant #{i + 1}",
                    f"Dimension shift: {', '.join(dimensions)}",
                ],
            )
            variations.append(variant)
            self._concepts[variant.id] = variant
            self._total_concepts += 1

        return variations

    def generate_pitch(self, concept_id: str) -> Dict[str, Any]:
        concept = self._concepts.get(concept_id)
        if not concept:
            return {"error": f"Concept '{concept_id}' not found"}

        fun_eval = self.evaluate_fun_factor(concept_id)

        return {
            "concept_id": concept_id,
            "title": concept.title,
            "genre": concept.genre,
            "core_mechanic": concept.core_mechanic,
            "secondary_mechanics": concept.secondary_mechanics,
            "theme": concept.theme,
            "unique_selling_point": concept.unique_selling_point or f"A {concept.genre} game with innovative {concept.core_mechanic} mechanics",
            "target_audience": concept.target_audience or f"Fans of {concept.genre} games and {concept.core_mechanic.replace('_', ' ')} enthusiasts",
            "complexity_rating": round(concept.complexity_score * 10, 1),
            "innovation_rating": round(concept.innovation_score * 10, 1),
            "feasibility_rating": round(concept.feasibility_score * 10, 1),
            "fun_factor_rating": round(fun_eval.get("fun_factor", 0.5) * 10, 1),
            "engagement_breakdown": fun_eval.get("engagement_scores", {}),
            "design_patterns": fun_eval.get("design_patterns_matched", []),
            "design_notes": concept.design_notes,
            "iteration_count": concept.iteration_count,
            "phase": concept.phase,
        }

    def compare_concepts(self, concept_ids: List[str]) -> Dict[str, Any]:
        results = {}
        for cid in concept_ids:
            concept = self._concepts.get(cid)
            if not concept:
                continue
            results[cid] = {
                "title": concept.title,
                "complexity": concept.complexity_score,
                "innovation": concept.innovation_score,
                "feasibility": concept.feasibility_score,
                "fun_factor": concept.fun_factor,
            }

        if not results:
            return {"error": "No valid concepts found"}

        scores = list(results.values())
        best_overall = max(results.keys(), key=lambda cid: results[cid]["fun_factor"])
        most_innovative = max(results.keys(), key=lambda cid: results[cid]["innovation"])
        most_feasible = max(results.keys(), key=lambda cid: results[cid]["feasibility"])

        return {
            "compared_concepts": results,
            "best_overall": best_overall,
            "most_innovative": most_innovative,
            "most_feasible": most_feasible,
            "recommendation": (
                f"'{results[best_overall]['title']}' offers the strongest player engagement, "
                f"while '{results[most_feasible]['title']}' is the most practical to implement"
            ),
        }

    def get_concept(self, concept_id: str) -> Optional[DesignConcept]:
        return self._concepts.get(concept_id)

    def get_session(self, session_id: str) -> Optional[DesignSession]:
        return self._sessions.get(session_id)

    def list_concepts(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._concepts.values()]

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values()]

    def get_stats(self) -> Dict[str, Any]:
        domain_distribution: Dict[str, int] = {}
        for concept in self._concepts.values():
            domain_distribution[concept.domain] = domain_distribution.get(concept.domain, 0) + 1

        return {
            "total_concepts": self._total_concepts,
            "total_analyses": self._total_analyses,
            "total_predictions": self._total_predictions,
            "total_sessions": self._total_sessions,
            "total_brainstorms": self._total_brainstorms,
            "active_session": self._active_session_id,
            "concepts_by_domain": domain_distribution,
            "average_fun_factor": round(
                sum(c.fun_factor for c in self._concepts.values()) / max(len(self._concepts), 1), 3
            ),
            "knowledge_base_size": len(_MECHANIC_KNOWLEDGE_BASE),
            "design_patterns_available": len(_DESIGN_PATTERNS),
        }


def get_game_design_intelligence() -> GameDesignIntelligence:
    return GameDesignIntelligence.get_instance()