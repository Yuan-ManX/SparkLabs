"""
SparkLabs Agent - Game Intelligence Engine

A comprehensive game intelligence system that provides AI-powered game analysis,
design optimization, and quality evaluation. It analyzes game states, identifies
design patterns, suggests improvements, and evaluates game experiences across
multiple dimensions and player archetypes.

Architecture:
  GameIntelligenceEngine (singleton)
    |-- GameStateAnalyzer (analyzes current game state for insights)
    |-- DesignPatternDetector (detects existing and missing design patterns)
    |-- QualityEvaluator (evaluates game quality across multiple dimensions)
    |-- SuggestionGenerator (generates prioritized improvement suggestions)
    |-- PlayerExperienceModeler (models player experience for different archetypes)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------------ Enums ------------------------------------------------------------------


class AnalysisDomain(Enum):
    GAMEPLAY = "gameplay"
    BALANCE = "balance"
    PACING = "pacing"
    DIFFICULTY = "difficulty"
    ENGAGEMENT = "engagement"
    AESTHETICS = "aesthetics"
    NARRATIVE = "narrative"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    MONETIZATION = "monetization"


class DesignPattern(Enum):
    FEEDBACK_LOOP = "feedback_loop"
    RISK_REWARD = "risk_reward"
    PROGRESSION_CURVE = "progression_curve"
    EMERGENT_GAMEPLAY = "emergent_gameplay"
    SKILL_MASTERY = "skill_mastery"
    SOCIAL_DYNAMICS = "social_dynamics"
    EXPLORATION_REWARD = "exploration_reward"
    TIME_PRESSURE = "time_pressure"
    RESOURCE_SCARCITY = "resource_scarcity"
    PATTERN_RECOGNITION = "pattern_recognition"


class QualityDimension(Enum):
    FUN_FACTOR = "fun_factor"
    POLISH = "polish"
    INNOVATION = "innovation"
    REPLAYABILITY = "replayability"
    LEARNING_CURVE = "learning_curve"
    BALANCE = "balance"
    IMMERSION = "immersion"
    TECHNICAL_QUALITY = "technical_quality"


class SuggestionPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    COSMETIC = "cosmetic"


class PlayerArchetype(Enum):
    ACHIEVER = "achiever"
    EXPLORER = "explorer"
    SOCIALIZER = "socializer"
    KILLER = "killer"
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    CASUAL = "casual"
    HARDCORE = "hardcore"


# ---------------------------------------------------------------- Dataclasses ----------------------------------------------------------------


@dataclass
class GameStateSnapshot:
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    active_scene: str = ""
    player_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    game_phase: str = "menu"
    entities_count: int = 0
    fps: float = 60.0
    memory_usage: float = 0.0
    interaction_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id, "timestamp": self.timestamp,
            "active_scene": self.active_scene, "player_position": list(self.player_position),
            "game_phase": self.game_phase, "entities_count": self.entities_count,
            "fps": self.fps, "memory_usage": self.memory_usage,
            "interaction_count": self.interaction_count,
        }


@dataclass
class DesignAnalysis:
    analysis_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    domain: AnalysisDomain = AnalysisDomain.GAMEPLAY
    patterns_found: List[DesignPattern] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    innovation_score: float = 0.0
    coherence_score: float = 0.0
    analyzed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id, "domain": self.domain.value,
            "patterns_found": [p.value for p in self.patterns_found],
            "strengths": list(self.strengths), "weaknesses": list(self.weaknesses),
            "opportunities": list(self.opportunities), "threats": list(self.threats),
            "innovation_score": round(self.innovation_score, 2),
            "coherence_score": round(self.coherence_score, 2),
            "analyzed_at": self.analyzed_at,
        }


@dataclass
class QualityEvaluation:
    evaluation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    dimensions_scores: Dict[QualityDimension, float] = field(default_factory=dict)
    overall_score: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    benchmark_comparison: Dict[str, float] = field(default_factory=dict)
    player_feedback_summary: str = ""
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "dimensions_scores": {k.value: round(v, 2) for k, v in self.dimensions_scores.items()},
            "overall_score": round(self.overall_score, 2),
            "confidence_interval": list(self.confidence_interval),
            "benchmark_comparison": dict(self.benchmark_comparison),
            "player_feedback_summary": self.player_feedback_summary,
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class ImprovementSuggestion:
    suggestion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_area: str = ""
    priority: SuggestionPriority = SuggestionPriority.MEDIUM
    description: str = ""
    expected_impact: float = 0.0
    implementation_complexity: float = 0.0
    risk_assessment: str = ""
    alternatives: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id, "target_area": self.target_area,
            "priority": self.priority.value, "description": self.description,
            "expected_impact": round(self.expected_impact, 2),
            "implementation_complexity": round(self.implementation_complexity, 2),
            "risk_assessment": self.risk_assessment, "alternatives": list(self.alternatives),
            "created_at": self.created_at,
        }


@dataclass
class PlayerExperienceModel:
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    archetype: PlayerArchetype = PlayerArchetype.CASUAL
    engagement_curve: List[Tuple[float, float]] = field(default_factory=list)
    frustration_points: List[str] = field(default_factory=list)
    flow_states: List[str] = field(default_factory=list)
    satisfaction_peaks: List[str] = field(default_factory=list)
    dropout_risks: List[str] = field(default_factory=list)
    modeled_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id, "archetype": self.archetype.value,
            "engagement_curve": [[round(x, 2), round(y, 2)] for x, y in self.engagement_curve],
            "frustration_points": list(self.frustration_points),
            "flow_states": list(self.flow_states),
            "satisfaction_peaks": list(self.satisfaction_peaks),
            "dropout_risks": list(self.dropout_risks), "modeled_at": self.modeled_at,
        }


@dataclass
class GameBalanceReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mechanics_balance: Dict[str, float] = field(default_factory=dict)
    difficulty_curve: List[Tuple[float, float]] = field(default_factory=list)
    economy_health: float = 0.0
    progression_speed: float = 0.0
    power_creep_risk: float = 0.0
    fairness_score: float = 0.0
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id, "mechanics_balance": dict(self.mechanics_balance),
            "difficulty_curve": [[round(x, 2), round(y, 2)] for x, y in self.difficulty_curve],
            "economy_health": round(self.economy_health, 2),
            "progression_speed": round(self.progression_speed, 2),
            "power_creep_risk": round(self.power_creep_risk, 2),
            "fairness_score": round(self.fairness_score, 2),
            "generated_at": self.generated_at,
        }


# -------------------------------------------------------------- GameStateAnalyzer --------------------------------------------------------------


class GameStateAnalyzer:
    """Analyzes game state snapshots to extract gameplay and performance insights."""

    _PHASE_PATTERNS: Dict[str, Tuple[int, float, int]] = {
        "menu": (0, 60.0, 0), "loading": (0, 30.0, 0),
        "gameplay": (50, 60.0, 20), "combat": (30, 60.0, 50),
        "cinematic": (10, 30.0, 0), "pause": (0, 60.0, 0),
    }

    def __init__(self) -> None:
        self._snapshot_history: deque = deque(maxlen=200)
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}

    def analyze_snapshot(self, snapshot: GameStateSnapshot) -> Dict[str, Any]:
        self._snapshot_history.append(snapshot)
        exp_entities, exp_fps, exp_interactions = self._PHASE_PATTERNS.get(
            snapshot.game_phase, (0, 60.0, 0))

        entity_ratio = snapshot.entities_count / max(exp_entities, 1)
        fps_ratio = snapshot.fps / max(exp_fps, 1)
        interaction_ratio = snapshot.interaction_count / max(exp_interactions, 1)

        anomalies: List[str] = []
        if entity_ratio > 2.0:
            anomalies.append("entity_overload")
        elif entity_ratio < 0.1 and exp_entities > 0:
            anomalies.append("entity_starvation")
        if fps_ratio < 0.5:
            anomalies.append("performance_degradation")
        if interaction_ratio > 3.0:
            anomalies.append("interaction_spike")

        fps_status = ("excellent" if snapshot.fps >= 55 else
                      "acceptable" if snapshot.fps >= 30 else
                      "poor" if snapshot.fps >= 15 else "critical")
        mem_status = ("low" if snapshot.memory_usage < 512 else
                      "moderate" if snapshot.memory_usage < 2048 else
                      "high" if snapshot.memory_usage < 4096 else "critical")
        phase_status = "critical" if len(anomalies) > 2 else ("warning" if anomalies else "normal")
        issues = ((3 if phase_status == "critical" else 1 if phase_status == "warning" else 0) +
                  (2 if fps_status in ("poor", "critical") else 0) +
                  (2 if mem_status == "critical" else 0))
        health = ("excellent" if issues == 0 else "good" if issues <= 2 else
                  "fair" if issues <= 4 else "poor")

        insights = {
            "snapshot_id": snapshot.snapshot_id, "phase": snapshot.game_phase,
            "entity_ratio": round(entity_ratio, 2), "fps_ratio": round(fps_ratio, 2),
            "interaction_ratio": round(interaction_ratio, 2), "fps_status": fps_status,
            "memory_status": mem_status, "anomalies": anomalies, "overall_health": health,
        }
        self._analysis_cache[snapshot.snapshot_id] = insights
        return insights

    def get_recent_insights(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [self._analysis_cache.get(s.snapshot_id, {})
                for s in list(self._snapshot_history)[-limit:]]


# ------------------------------------------------------------ DesignPatternDetector ------------------------------------------------------------


class DesignPatternDetector:
    """Detects existing and missing design patterns in game configurations."""

    _INDICATORS: Dict[DesignPattern, List[str]] = {
        DesignPattern.FEEDBACK_LOOP: ["rewards", "score", "combo", "multiplier", "achievement"],
        DesignPattern.RISK_REWARD: ["danger", "high_stakes", "trade_off", "sacrifice", "penalty"],
        DesignPattern.PROGRESSION_CURVE: ["level_up", "xp", "skill_tree", "unlock", "tier", "upgrade"],
        DesignPattern.EMERGENT_GAMEPLAY: ["sandbox", "physics", "simulation", "procedural", "dynamic"],
        DesignPattern.SKILL_MASTERY: ["practice", "technique", "timing", "precision", "mastery"],
        DesignPattern.SOCIAL_DYNAMICS: ["multiplayer", "guild", "trade", "coop", "pvp", "leaderboard"],
        DesignPattern.EXPLORATION_REWARD: ["hidden", "secret", "discover", "explore", "treasure", "lore"],
        DesignPattern.TIME_PRESSURE: ["timer", "countdown", "deadline", "race", "speed"],
        DesignPattern.RESOURCE_SCARCITY: ["limited", "rare", "scarcity", "ration", "survival"],
        DesignPattern.PATTERN_RECOGNITION: ["puzzle", "sequence", "rhythm", "match", "pattern", "solve"],
    }

    _SYNERGIES: Dict[DesignPattern, List[DesignPattern]] = {
        DesignPattern.FEEDBACK_LOOP: [DesignPattern.PROGRESSION_CURVE, DesignPattern.SKILL_MASTERY],
        DesignPattern.RISK_REWARD: [DesignPattern.TIME_PRESSURE, DesignPattern.RESOURCE_SCARCITY],
        DesignPattern.PROGRESSION_CURVE: [DesignPattern.SKILL_MASTERY, DesignPattern.FEEDBACK_LOOP],
        DesignPattern.EMERGENT_GAMEPLAY: [DesignPattern.EXPLORATION_REWARD, DesignPattern.SOCIAL_DYNAMICS],
        DesignPattern.SKILL_MASTERY: [DesignPattern.PROGRESSION_CURVE, DesignPattern.TIME_PRESSURE],
        DesignPattern.EXPLORATION_REWARD: [DesignPattern.EMERGENT_GAMEPLAY, DesignPattern.PATTERN_RECOGNITION],
        DesignPattern.TIME_PRESSURE: [DesignPattern.RISK_REWARD, DesignPattern.SKILL_MASTERY],
        DesignPattern.RESOURCE_SCARCITY: [DesignPattern.RISK_REWARD, DesignPattern.PROGRESSION_CURVE],
    }

    def __init__(self) -> None:
        self._detection_history: List[Dict[str, Any]] = []

    def detect_patterns(self, game_config: Dict[str, Any]) -> List[DesignPattern]:
        config_text = json.dumps(game_config).lower()
        detected: List[DesignPattern] = []
        scores: Dict[str, float] = {}
        for pattern, indicators in self._INDICATORS.items():
            coverage = sum(1 for ind in indicators if ind in config_text) / len(indicators)
            score = round(coverage + random.uniform(-0.1, 0.15), 3)
            scores[pattern.value] = score
            if score >= 0.35:
                detected.append(pattern)
        self._detection_history.append({
            "timestamp": time.time(), "detected": [p.value for p in detected], "scores": scores,
        })
        return detected

    def get_missing_patterns(self, detected: List[DesignPattern]) -> List[DesignPattern]:
        return [p for p in DesignPattern if p not in detected]

    def get_recommended_patterns(self, detected: List[DesignPattern]) -> List[Tuple[DesignPattern, str]]:
        recommendations: List[Tuple[DesignPattern, str]] = []
        seen: List[DesignPattern] = []
        for pattern in detected:
            for syn in self._SYNERGIES.get(pattern, []):
                if syn not in detected and syn not in seen:
                    recommendations.append((syn, f"Complements {pattern.value}"))
                    seen.append(syn)
        return recommendations[:5]

    def get_detection_history(self) -> List[Dict[str, Any]]:
        return list(self._detection_history)


# --------------------------------------------------------------- QualityEvaluator ---------------------------------------------------------------


class QualityEvaluator:
    """Evaluates game quality across multiple dimensions with benchmark comparison."""

    _WEIGHTS: Dict[QualityDimension, float] = {
        QualityDimension.FUN_FACTOR: 0.25, QualityDimension.POLISH: 0.15,
        QualityDimension.INNOVATION: 0.10, QualityDimension.REPLAYABILITY: 0.12,
        QualityDimension.LEARNING_CURVE: 0.08, QualityDimension.BALANCE: 0.10,
        QualityDimension.IMMERSION: 0.10, QualityDimension.TECHNICAL_QUALITY: 0.10,
    }
    _BENCHMARKS: Dict[str, float] = {
        "indie_average": 0.72, "aa_average": 0.78, "aaa_average": 0.84, "masterpiece": 0.92,
    }
    _MODIFIERS: Dict[QualityDimension, float] = {
        QualityDimension.FUN_FACTOR: 0.10, QualityDimension.POLISH: -0.05,
        QualityDimension.INNOVATION: 0.08, QualityDimension.REPLAYABILITY: 0.02,
        QualityDimension.LEARNING_CURVE: -0.03, QualityDimension.BALANCE: 0.0,
        QualityDimension.IMMERSION: 0.05, QualityDimension.TECHNICAL_QUALITY: -0.02,
    }

    def __init__(self) -> None:
        self._evaluation_history: List[QualityEvaluation] = []

    def evaluate(self, analysis: DesignAnalysis) -> QualityEvaluation:
        base = (0.50 + len(analysis.patterns_found) * 0.04 +
                len(analysis.strengths) * 0.03 - len(analysis.weaknesses) * 0.05 +
                analysis.innovation_score * 0.15 + analysis.coherence_score * 0.10)
        dim_scores: Dict[QualityDimension, float] = {}
        for dim in QualityDimension:
            s = base + self._MODIFIERS.get(dim, 0.0) + random.uniform(-0.06, 0.06)
            dim_scores[dim] = round(max(0.0, min(1.0, s)), 2)
        overall = round(sum(dim_scores[d] * self._WEIGHTS[d] for d in QualityDimension), 2)
        margin = random.uniform(0.03, 0.08)
        confidence = (round(max(0.0, overall - margin), 2), round(min(1.0, overall + margin), 2))
        benchmarks = {t: round(overall - s, 2) for t, s in self._BENCHMARKS.items()}
        top_dim = max(dim_scores, key=lambda d: dim_scores[d])  # type: ignore[arg-type]
        low_dim = min(dim_scores, key=lambda d: dim_scores[d])  # type: ignore[arg-type]
        tier = ("exceptional" if overall >= 0.85 else "solid" if overall >= 0.70 else
                "average" if overall >= 0.50 else "needs improvement")
        feedback = (f"Overall quality is {tier} ({overall:.2f}). "
                    f"Strongest: {top_dim.value}. Needs work: {low_dim.value}.")
        evaluation = QualityEvaluation(
            dimensions_scores=dim_scores, overall_score=overall,
            confidence_interval=confidence, benchmark_comparison=benchmarks,
            player_feedback_summary=feedback,
        )
        self._evaluation_history.append(evaluation)
        return evaluation

    def get_evaluation_history(self) -> List[QualityEvaluation]:
        return list(self._evaluation_history)

    def get_latest_evaluation(self) -> Optional[QualityEvaluation]:
        return self._evaluation_history[-1] if self._evaluation_history else None


# ------------------------------------------------------------- SuggestionGenerator -------------------------------------------------------------


class SuggestionGenerator:
    """Generates prioritized improvement suggestions based on design analysis."""

    _TEMPLATES: Dict[AnalysisDomain, List[str]] = {
        AnalysisDomain.GAMEPLAY: [
            "Enhance core loop with tighter feedback cycles",
            "Introduce secondary mechanics for depth",
            "Add meaningful player choices with consequences",
        ],
        AnalysisDomain.BALANCE: [
            "Normalize damage output across character classes",
            "Adjust resource economy to reduce inflation",
            "Rebalance risk-reward ratios in high-stakes encounters",
        ],
        AnalysisDomain.PACING: [
            "Insert breather segments between high-intensity sections",
            "Vary encounter density to prevent monotony",
            "Implement dynamic pacing that adapts to player behavior",
        ],
        AnalysisDomain.DIFFICULTY: [
            "Smooth the difficulty curve at early levels",
            "Add optional challenge modifiers for experienced players",
            "Implement adaptive difficulty based on player performance",
        ],
        AnalysisDomain.ENGAGEMENT: [
            "Introduce daily challenges to boost retention",
            "Add social features for community interaction",
            "Create seasonal events for long-term engagement",
        ],
        AnalysisDomain.AESTHETICS: [
            "Improve visual clarity of UI elements",
            "Enhance environmental storytelling through art",
            "Refine color palette for better readability",
        ],
        AnalysisDomain.NARRATIVE: [
            "Deepen character backstories for emotional investment",
            "Add branching dialogue with meaningful outcomes",
            "Integrate lore into environmental details",
        ],
        AnalysisDomain.ACCESSIBILITY: [
            "Add colorblind mode options",
            "Implement full controller remapping",
            "Add difficulty presets with granular adjustments",
        ],
        AnalysisDomain.PERFORMANCE: [
            "Optimize draw calls for complex scenes",
            "Implement level-of-detail system for distant objects",
            "Reduce memory allocation during gameplay",
        ],
        AnalysisDomain.MONETIZATION: [
            "Ensure all gameplay content is earnable without purchase",
            "Add transparent pricing for cosmetic items",
            "Implement fair battle pass progression",
        ],
    }

    _PRIORITY_ORDER = [SuggestionPriority.COSMETIC, SuggestionPriority.LOW,
                       SuggestionPriority.MEDIUM, SuggestionPriority.HIGH, SuggestionPriority.CRITICAL]

    def __init__(self) -> None:
        self._suggestion_history: List[ImprovementSuggestion] = []

    def generate_suggestions(
        self, analysis: DesignAnalysis, domain: Optional[AnalysisDomain] = None
    ) -> List[ImprovementSuggestion]:
        domains = [domain] if domain else list(AnalysisDomain)
        suggestions: List[ImprovementSuggestion] = []
        for dom in domains:
            templates = self._TEMPLATES.get(dom, [])
            count = random.randint(1, min(3, len(templates)))
            selected = random.sample(templates, count) if len(templates) >= count else templates
            w = len(analysis.weaknesses)
            c = analysis.coherence_score
            if w > 3 or c < 0.3:
                priority = SuggestionPriority.CRITICAL
            elif w > 1 or c < 0.5:
                priority = SuggestionPriority.HIGH
            elif c < 0.7:
                priority = SuggestionPriority.MEDIUM
            elif c < 0.85:
                priority = SuggestionPriority.LOW
            else:
                priority = SuggestionPriority.COSMETIC
            for template in selected:
                impact = round(random.uniform(0.2, 0.95), 2)
                complexity = round(random.uniform(0.1, 0.9), 2)
                if priority == SuggestionPriority.CRITICAL and complexity > 0.7:
                    risk = "High risk — urgent change with significant effort"
                elif priority in (SuggestionPriority.HIGH, SuggestionPriority.CRITICAL):
                    risk = "Moderate risk — important change with manageable complexity"
                elif complexity > 0.6:
                    risk = "Low risk — minor improvement with moderate effort"
                else:
                    risk = "Minimal risk — straightforward change"
                suggestions.append(ImprovementSuggestion(
                    target_area=dom.value, priority=priority, description=template,
                    expected_impact=impact, implementation_complexity=complexity,
                    risk_assessment=risk, alternatives=[f"Alternative approach for {dom.value}"],
                ))
        suggestions.sort(key=lambda s: self._PRIORITY_ORDER.index(s.priority), reverse=True)
        self._suggestion_history.extend(suggestions)
        return suggestions

    def get_suggestion_history(self) -> List[ImprovementSuggestion]:
        return list(self._suggestion_history)


# ----------------------------------------------------------- PlayerExperienceModeler -----------------------------------------------------------


class PlayerExperienceModeler:
    """Models player experience for different archetypes to predict engagement."""

    _PROFILES: Dict[PlayerArchetype, Dict[str, List[str]]] = {
        PlayerArchetype.ACHIEVER: {
            "frustration_triggers": ["gated_content", "low_rewards", "grindy_tasks"],
            "flow_preferences": ["clear_goals", "measurable_progress", "challenge_ladders"],
            "satisfaction_sources": ["100_percent_completion", "rare_achievements", "high_score"],
            "dropout_risks": ["content_drought", "meaningless_grind", "unfair_competition"],
        },
        PlayerArchetype.EXPLORER: {
            "frustration_triggers": ["invisible_walls", "linear_paths", "repetitive_environments"],
            "flow_preferences": ["open_world", "environmental_puzzles", "branching_paths"],
            "satisfaction_sources": ["secret_areas", "environmental_storytelling", "easter_eggs"],
            "dropout_risks": ["empty_world", "on_rails_design", "lack_of_discovery"],
        },
        PlayerArchetype.SOCIALIZER: {
            "frustration_triggers": ["forced_solo", "toxic_environment", "no_guild_system"],
            "flow_preferences": ["group_content", "trading", "social_hubs"],
            "satisfaction_sources": ["teamwork_victories", "helping_others", "social_recognition"],
            "dropout_risks": ["lonely_experience", "poor_communication_tools", "dead_community"],
        },
        PlayerArchetype.KILLER: {
            "frustration_triggers": ["unbalanced_pvp", "cheaters", "no_ranking"],
            "flow_preferences": ["ranked_modes", "duels", "tournaments"],
            "satisfaction_sources": ["winning_streaks", "top_rank", "dominating_opponents"],
            "dropout_risks": ["stale_meta", "unfair_matchmaking", "lack_of_competition"],
        },
        PlayerArchetype.COMPLETIONIST: {
            "frustration_triggers": ["missable_content", "grindy_collectibles", "timed_exclusives"],
            "flow_preferences": ["completion_tracking", "checklists", "reward_milestones"],
            "satisfaction_sources": ["full_completion", "rare_collections", "platinum_trophies"],
            "dropout_risks": ["unobtainable_items", "endless_grind", "repetitive_tasks"],
        },
        PlayerArchetype.SPEEDRUNNER: {
            "frustration_triggers": ["unskippable_cutscenes", "rng_dependency", "slow_segments"],
            "flow_preferences": ["tight_controls", "skip_techniques", "leaderboard_timers"],
            "satisfaction_sources": ["world_records", "new_strategies", "perfect_execution"],
            "dropout_risks": ["patched_skips", "no_speedrun_community", "unoptimizable_segments"],
        },
        PlayerArchetype.CASUAL: {
            "frustration_triggers": ["high_difficulty", "complex_systems", "long_sessions"],
            "flow_preferences": ["simple_mechanics", "forgiving_design", "bite_sized_content"],
            "satisfaction_sources": ["easy_progress", "pleasant_aesthetics", "low_stress"],
            "dropout_risks": ["difficulty_spikes", "overwhelming_complexity", "time_demands"],
        },
        PlayerArchetype.HARDCORE: {
            "frustration_triggers": ["hand_holding", "easy_mode", "lack_of_depth"],
            "flow_preferences": ["high_difficulty", "complex_systems", "permadeath"],
            "satisfaction_sources": ["overcoming_challenge", "optimal_builds", "perfect_play"],
            "dropout_risks": ["too_easy", "shallow_mechanics", "lack_of_mastery_path"],
        },
    }

    def __init__(self) -> None:
        self._model_history: List[PlayerExperienceModel] = []

    def model_experience(
        self, archetype: PlayerArchetype, game_config: Dict[str, Any]
    ) -> PlayerExperienceModel:
        profile = self._PROFILES.get(archetype, self._PROFILES[PlayerArchetype.CASUAL])
        config_text = json.dumps(game_config).lower()
        curve: List[Tuple[float, float]] = []
        for i in range(20):
            t = i / 19.0
            if archetype in (PlayerArchetype.HARDCORE, PlayerArchetype.SPEEDRUNNER):
                eng = 0.4 + 0.5 * t + 0.1 * math.sin(t * math.pi * 3)
            elif archetype == PlayerArchetype.CASUAL:
                eng = 0.6 + 0.2 * math.sin(t * math.pi * 2)
            else:
                eng = 0.5 + 0.3 * math.sin(t * math.pi * 2.5) + 0.15 * t
            eng = max(0.0, min(1.0, eng + random.uniform(-0.05, 0.05)))
            curve.append((round(t, 2), round(eng, 2)))
        frustration = [t for t in profile["frustration_triggers"]
                       if t.replace("_", " ") not in config_text][:3]
        flow = [p for p in profile["flow_preferences"]
                if any(w in config_text for w in p.replace("_", " ").split())][:3]
        model = PlayerExperienceModel(
            archetype=archetype, engagement_curve=curve,
            frustration_points=frustration, flow_states=flow,
            satisfaction_peaks=profile["satisfaction_sources"][:3],
            dropout_risks=profile["dropout_risks"][:3],
        )
        self._model_history.append(model)
        return model

    def get_model_history(self) -> List[PlayerExperienceModel]:
        return list(self._model_history)


# ---------------------------------------------------------- GameIntelligenceEngine -----------------------------------------------------------


class GameIntelligenceEngine:
    """Orchestrates all game intelligence subsystems for comprehensive analysis.

    Provides a unified interface for game state analysis, design pattern detection,
    quality evaluation, improvement suggestion generation, player experience modeling,
    and balance reporting. Implements thread-safe singleton pattern.
    """

    _instance: Optional["GameIntelligenceEngine"] = None
    _lock = threading.RLock()

    _PHASE_DOMAIN_MAP: Dict[str, AnalysisDomain] = {
        "menu": AnalysisDomain.ACCESSIBILITY, "loading": AnalysisDomain.PERFORMANCE,
        "gameplay": AnalysisDomain.GAMEPLAY, "combat": AnalysisDomain.BALANCE,
        "cinematic": AnalysisDomain.NARRATIVE, "pause": AnalysisDomain.ACCESSIBILITY,
    }

    def __init__(self) -> None:
        self._state_analyzer = GameStateAnalyzer()
        self._pattern_detector = DesignPatternDetector()
        self._quality_evaluator = QualityEvaluator()
        self._suggestion_generator = SuggestionGenerator()
        self._experience_modeler = PlayerExperienceModeler()
        self._analysis_history: List[DesignAnalysis] = []
        self._report_history: List[GameBalanceReport] = []
        self._session_count: int = 0
        self._total_analyses: int = 0
        self._engine_version: str = "2.0.0"
        self._started_at: float = time.time()

    @classmethod
    def get_instance(cls) -> "GameIntelligenceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Core Analysis Methods ----

    def analyze_game_state(self, snapshot: GameStateSnapshot) -> DesignAnalysis:
        self._state_analyzer.analyze_snapshot(snapshot)
        domain = self._PHASE_DOMAIN_MAP.get(snapshot.game_phase, AnalysisDomain.GAMEPLAY)
        patterns = self._pattern_detector.detect_patterns({
            "scene": snapshot.active_scene, "phase": snapshot.game_phase,
            "entities": snapshot.entities_count, "interactions": snapshot.interaction_count,
        })
        strengths: List[str] = []
        if snapshot.fps >= 55.0:
            strengths.append("Smooth performance with stable frame rate")
        if snapshot.entities_count > 0:
            strengths.append("Active entity management in current scene")
        if snapshot.interaction_count > 10:
            strengths.append("High player interaction density")
        if len(patterns) >= 3:
            strengths.append(f"Rich design pattern composition ({len(patterns)} patterns detected)")
        if snapshot.memory_usage < 2048:
            strengths.append("Efficient memory utilization")
        if not strengths:
            strengths.append("Baseline functionality present")

        weaknesses: List[str] = []
        if snapshot.fps < 30.0:
            weaknesses.append("Frame rate below acceptable threshold")
        if snapshot.memory_usage > 4096:
            weaknesses.append("High memory consumption may impact stability")
        if snapshot.entities_count == 0 and snapshot.game_phase == "gameplay":
            weaknesses.append("No active entities during gameplay phase")
        if snapshot.interaction_count == 0 and snapshot.game_phase == "gameplay":
            weaknesses.append("Zero player interactions during gameplay")

        opportunities: List[str] = []
        if DesignPattern.FEEDBACK_LOOP not in patterns:
            opportunities.append("Introduce feedback loops for player actions")
        if DesignPattern.RISK_REWARD not in patterns:
            opportunities.append("Add risk-reward decision points")
        if DesignPattern.EXPLORATION_REWARD not in patterns:
            opportunities.append("Incorporate exploration rewards for discovery")
        if snapshot.entities_count < 20 and snapshot.game_phase == "gameplay":
            opportunities.append("Increase entity density for richer gameplay")

        threats: List[str] = []
        if snapshot.fps < 25.0:
            threats.append("Performance degradation may cause player churn")
        if snapshot.memory_usage > 6000:
            threats.append("Memory pressure risks crashes on lower-end hardware")
        if snapshot.game_phase == "menu" and snapshot.interaction_count > 50:
            threats.append("Menu complexity may overwhelm new players")

        innovation = round(random.uniform(0.3, 0.9), 2)
        coherence = round(0.5 + len(patterns) * 0.06 - len(weaknesses) * 0.08 +
                          random.uniform(-0.05, 0.05), 2)
        coherence = max(0.0, min(1.0, coherence))

        analysis = DesignAnalysis(
            domain=domain, patterns_found=patterns, strengths=strengths,
            weaknesses=weaknesses, opportunities=opportunities, threats=threats,
            innovation_score=innovation, coherence_score=coherence,
        )
        self._analysis_history.append(analysis)
        self._total_analyses += 1
        return analysis

    def evaluate_quality(self, analysis: DesignAnalysis) -> QualityEvaluation:
        return self._quality_evaluator.evaluate(analysis)

    def generate_suggestions(
        self, analysis: DesignAnalysis, domain: Optional[AnalysisDomain] = None
    ) -> List[ImprovementSuggestion]:
        return self._suggestion_generator.generate_suggestions(analysis, domain)

    def detect_patterns(self, game_config: Dict[str, Any]) -> List[DesignPattern]:
        return self._pattern_detector.detect_patterns(game_config)

    def model_player_experience(
        self, archetype: PlayerArchetype, game_config: Dict[str, Any]
    ) -> PlayerExperienceModel:
        return self._experience_modeler.model_experience(archetype, game_config)

    def generate_balance_report(self, mechanics: Dict[str, Any]) -> GameBalanceReport:
        mech_balance: Dict[str, float] = {}
        for mech_name in mechanics:
            if mech_name != "num_levels":
                mech_balance[mech_name] = round(random.uniform(0.3, 1.0), 2)
        num_levels = max(5, mechanics.get("num_levels", 10))
        difficulty_curve: List[Tuple[float, float]] = []
        for i in range(num_levels):
            level = i + 1
            normalized = (level - 1) / max(num_levels - 1, 1)
            difficulty = 0.1 + 0.8 * (normalized ** 1.3) + random.uniform(-0.05, 0.05)
            difficulty_curve.append((float(level), round(max(0.0, min(1.0, difficulty)), 2)))
        fairness = round(0.5 + (sum(mech_balance.values()) / max(len(mech_balance), 1)) * 0.3 +
                         random.uniform(-0.08, 0.08), 2)
        report = GameBalanceReport(
            mechanics_balance=mech_balance, difficulty_curve=difficulty_curve,
            economy_health=round(random.uniform(0.4, 0.95), 2),
            progression_speed=round(random.uniform(0.3, 0.9), 2),
            power_creep_risk=round(random.uniform(0.1, 0.7), 2),
            fairness_score=max(0.0, min(1.0, fairness)),
        )
        self._report_history.append(report)
        return report

    # ---- History & Metrics ----

    def get_analysis_history(self) -> List[DesignAnalysis]:
        return list(self._analysis_history)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "engine_version": self._engine_version,
            "uptime_seconds": round(time.time() - self._started_at, 1),
            "session_count": self._session_count, "total_analyses": self._total_analyses,
            "analysis_history_size": len(self._analysis_history),
            "report_history_size": len(self._report_history),
            "suggestion_count": len(self._suggestion_generator.get_suggestion_history()),
            "evaluation_count": len(self._quality_evaluator.get_evaluation_history()),
            "model_count": len(self._experience_modeler.get_model_history()),
            "detection_queries": len(self._pattern_detector.get_detection_history()),
            "state_snapshots_analyzed": len(self._state_analyzer.get_recent_insights(limit=1000)),
        }

    # ---- Batch Operations ----

    def run_full_analysis(
        self, snapshot: GameStateSnapshot, game_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._session_count += 1
        design_analysis = self.analyze_game_state(snapshot)
        quality_eval = self.evaluate_quality(design_analysis)
        suggestions = self.generate_suggestions(design_analysis)
        patterns = self.detect_patterns(game_config)
        archetype_models: Dict[str, Dict[str, Any]] = {}
        for arch in [PlayerArchetype.CASUAL, PlayerArchetype.HARDCORE, PlayerArchetype.ACHIEVER]:
            archetype_models[arch.value] = self.model_player_experience(arch, game_config).to_dict()
        balance_report = self.generate_balance_report(game_config)
        return {
            "session_id": uuid.uuid4().hex[:12],
            "design_analysis": design_analysis.to_dict(),
            "quality_evaluation": quality_eval.to_dict(),
            "suggestions": [s.to_dict() for s in suggestions],
            "detected_patterns": [p.value for p in patterns],
            "player_experience_models": archetype_models,
            "balance_report": balance_report.to_dict(),
            "completed_at": time.time(),
        }


# ------------------------------------------------------------ Convenience Accessor ------------------------------------------------------------


def get_game_intelligence() -> GameIntelligenceEngine:
    """Return the singleton GameIntelligenceEngine instance."""
    return GameIntelligenceEngine.get_instance()