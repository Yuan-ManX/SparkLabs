"""
SparkLabs Agent - Player Modeler

Predictive player behavior intelligence that builds models of how different
player personas will experience and interact with a game. Simulates player
journeys, predicts engagement patterns, identifies frustration points,
and estimates session retention — all before real players touch the game.

Architecture:
  PlayerModeler
    |-- PersonaEngine (generates diverse synthetic player archetypes)
    |-- JourneySimulator (step-by-step player progression simulation)
    |-- EngagementPredictor (estimates retention curves and churn risk)
    |-- FrustrationDetector (identifies likely rage-quit and drop-off points)
    |-- SatisfactionEstimator (predicts net promoter scores and enjoyment)

Player Archetypes:
  - COMPLETIONIST: explores everything, 100% clears content
  - SPEEDRUNNER: optimizes for fastest completion
  - EXPLORER: wanders off-path, discovers hidden content
  - SOCIAL: engages with multiplayer and community features
  - CASUAL: plays in short bursts, low frustration tolerance
  - HARDCORE: seeks maximum challenge, min-maxes systems
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PlayerArchetype(Enum):
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    EXPLORER = "explorer"
    SOCIAL = "social"
    CASUAL = "casual"
    HARDCORE = "hardcore"


class SessionOutcome(Enum):
    ENGAGED = "engaged"
    NEUTRAL = "neutral"
    BORED = "bored"
    FRUSTRATED = "frustrated"
    RAGE_QUIT = "rage_quit"


class ContentCategory(Enum):
    MAIN_QUEST = "main_quest"
    SIDE_QUEST = "side_quest"
    EXPLORATION = "exploration"
    COMBAT = "combat"
    CRAFTING = "crafting"
    SOCIAL = "social"
    COLLECTION = "collection"


@dataclass
class PlayerPersona:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    archetype: PlayerArchetype = PlayerArchetype.CASUAL
    patience: float = 0.5
    skill_level: float = 0.5
    exploration_drive: float = 0.5
    completion_drive: float = 0.5
    social_drive: float = 0.5
    frustration_threshold: float = 0.5
    session_duration_preference: float = 1200.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "archetype": self.archetype.value,
            "patience": round(self.patience, 2),
            "skill_level": round(self.skill_level, 2),
            "exploration_drive": round(self.exploration_drive, 2),
            "completion_drive": round(self.completion_drive, 2),
            "social_drive": round(self.social_drive, 2),
            "frustration_threshold": round(self.frustration_threshold, 2),
            "session_duration_preference": self.session_duration_preference,
        }


@dataclass
class SimulatedSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    persona_id: str = ""
    game_id: str = ""
    session_number: int = 1
    duration_seconds: float = 0.0
    content_consumed: Dict[str, int] = field(default_factory=dict)
    difficulty_perceived: float = 0.5
    outcome: SessionOutcome = SessionOutcome.NEUTRAL
    satisfaction_score: float = 0.5
    frustration_events: int = 0
    quit_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "persona_id": self.persona_id,
            "game_id": self.game_id,
            "session_number": self.session_number,
            "duration_seconds": self.duration_seconds,
            "content_consumed": self.content_consumed,
            "difficulty_perceived": round(self.difficulty_perceived, 2),
            "outcome": self.outcome.value,
            "satisfaction_score": round(self.satisfaction_score, 2),
            "frustration_events": self.frustration_events,
            "quit_reason": self.quit_reason,
        }


@dataclass
class PlayerJourney:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    persona_id: str = ""
    game_id: str = ""
    sessions: List[SimulatedSession] = field(default_factory=list)
    total_playtime: float = 0.0
    total_sessions: int = 0
    longest_streak: int = 0
    churn_risk: float = 0.0
    estimated_retention_days: int = 0
    net_satisfaction: float = 0.0
    critical_frustration_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "persona_id": self.persona_id,
            "game_id": self.game_id,
            "sessions": [s.to_dict() for s in self.sessions],
            "total_playtime": round(self.total_playtime, 1),
            "total_sessions": self.total_sessions,
            "longest_streak": self.longest_streak,
            "churn_risk": round(self.churn_risk, 2),
            "estimated_retention_days": self.estimated_retention_days,
            "net_satisfaction": round(self.net_satisfaction, 2),
            "critical_frustration_points": self.critical_frustration_points,
        }


@dataclass
class GameExperienceReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_id: str = ""
    journeys: List[PlayerJourney] = field(default_factory=list)
    average_satisfaction: float = 0.0
    average_retention_days: float = 0.0
    overall_churn_risk: float = 0.0
    most_frustrating_content: str = ""
    most_engaging_content: str = ""
    archetype_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "journeys": [j.to_dict() for j in self.journeys],
            "average_satisfaction": round(self.average_satisfaction, 2),
            "average_retention_days": round(self.average_retention_days, 1),
            "overall_churn_risk": round(self.overall_churn_risk, 2),
            "most_frustrating_content": self.most_frustrating_content,
            "most_engaging_content": self.most_engaging_content,
            "archetype_performance": self.archetype_performance,
            "recommendations": self.recommendations,
        }


class PlayerModeler:
    """AI system for modeling and predicting player behavior patterns."""

    _instance: Optional["PlayerModeler"] = None
    _lock = threading.RLock()

    _ARCHETYPE_PRESETS: Dict[PlayerArchetype, Dict[str, Any]] = {
        PlayerArchetype.COMPLETIONIST: {
            "patience": 0.9, "skill": 0.6, "exploration": 0.9,
            "completion": 1.0, "social": 0.3, "frustration": 0.8,
            "session": 3600.0,
        },
        PlayerArchetype.SPEEDRUNNER: {
            "patience": 0.3, "skill": 0.9, "exploration": 0.1,
            "completion": 0.9, "social": 0.1, "frustration": 0.3,
            "session": 1800.0,
        },
        PlayerArchetype.EXPLORER: {
            "patience": 0.8, "skill": 0.5, "exploration": 1.0,
            "completion": 0.3, "social": 0.4, "frustration": 0.7,
            "session": 2400.0,
        },
        PlayerArchetype.SOCIAL: {
            "patience": 0.6, "skill": 0.5, "exploration": 0.5,
            "completion": 0.4, "social": 1.0, "frustration": 0.5,
            "session": 1800.0,
        },
        PlayerArchetype.CASUAL: {
            "patience": 0.4, "skill": 0.3, "exploration": 0.3,
            "completion": 0.2, "social": 0.5, "frustration": 0.2,
            "session": 600.0,
        },
        PlayerArchetype.HARDCORE: {
            "patience": 0.7, "skill": 0.9, "exploration": 0.6,
            "completion": 0.8, "social": 0.3, "frustration": 0.6,
            "session": 3600.0,
        },
    }

    def __init__(self) -> None:
        self._personas: Dict[str, PlayerPersona] = {}
        self._journeys: Dict[str, Dict[str, PlayerJourney]] = {}
        self._reports: Dict[str, GameExperienceReport] = {}
        self._simulation_history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "PlayerModeler":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Persona Generation ----

    def create_persona(self,
                       name: str = "",
                       archetype: str = "casual") -> PlayerPersona:
        try:
            arch = PlayerArchetype(archetype.lower())
        except ValueError:
            arch = PlayerArchetype.CASUAL
        preset = self._ARCHETYPE_PRESETS.get(arch, self._ARCHETYPE_PRESETS[PlayerArchetype.CASUAL])
        variance = lambda v: max(0.05, min(0.95, v + random.uniform(-0.1, 0.1)))
        persona = PlayerPersona(
            name=name or f"{arch.value.title()}_Player_{random.randint(100,999)}",
            archetype=arch,
            patience=variance(preset["patience"]),
            skill_level=variance(preset["skill"]),
            exploration_drive=variance(preset["exploration"]),
            completion_drive=variance(preset["completion"]),
            social_drive=variance(preset["social"]),
            frustration_threshold=variance(preset["frustration"]),
            session_duration_preference=preset["session"],
        )
        self._personas[persona.id] = persona
        return persona

    def seed_all_archetypes(self, suffix: str = "") -> List[PlayerPersona]:
        personas: List[PlayerPersona] = []
        for arch in PlayerArchetype:
            name = f"{arch.value.title()}{'_' + suffix if suffix else ''}"
            p = self.create_persona(name=name, archetype=arch.value)
            personas.append(p)
        return personas

    def get_persona(self, persona_id: str) -> Optional[PlayerPersona]:
        return self._personas.get(persona_id)

    def list_personas(self) -> List[PlayerPersona]:
        return list(self._personas.values())

    # ---- Journey Simulation ----

    def simulate_journey(self,
                         persona_id: str,
                         game_id: str,
                         max_sessions: int = 30) -> Optional[PlayerJourney]:
        persona = self._personas.get(persona_id)
        if persona is None:
            return None
        journey = PlayerJourney(persona_id=persona_id, game_id=game_id)
        streak = 0
        frustration_accumulator = 0.0

        for session_num in range(1, max_sessions + 1):
            session = self._simulate_single_session(persona, game_id, session_num,
                                                     frustration_accumulator)
            journey.sessions.append(session)
            journey.total_playtime += session.duration_seconds

            if session.outcome in (SessionOutcome.RAGE_QUIT, SessionOutcome.FRUSTRATED):
                frustration_accumulator += 0.15
                if session.outcome == SessionOutcome.RAGE_QUIT:
                    journey.critical_frustration_points.append(
                        f"Session {session_num}: rage quit triggered by {session.quit_reason}"
                    )
                    break
            else:
                frustration_accumulator = max(0.0, frustration_accumulator - 0.03)
                streak += 1
                journey.longest_streak = max(journey.longest_streak, streak)
                if session.outcome == SessionOutcome.BORED:
                    streak = 0

            if frustration_accumulator > 0.6:
                quit_session = self._create_frustrated_session(persona, game_id,
                                                                  session_num + 1)
                journey.sessions.append(quit_session)
                journey.critical_frustration_points.append(
                    f"Session {session_num + 1}: cumulative frustration ({frustration_accumulator:.2f}) caused quit"
                )
                break

        journey.total_sessions = len(journey.sessions)
        journey.churn_risk = self._calculate_churn_risk(journey)
        journey.net_satisfaction = self._calculate_satisfaction(journey)
        journey.estimated_retention_days = self._estimate_retention(journey)
        self._journeys.setdefault(game_id, {})[persona_id] = journey
        self._simulation_history.append({
            "action": "journey_simulated",
            "persona_id": persona_id,
            "game_id": game_id,
            "sessions": journey.total_sessions,
            "timestamp": time.time(),
        })
        return journey

    def _simulate_single_session(self,
                                 persona: PlayerPersona,
                                 game_id: str,
                                 session_num: int,
                                 frustration: float) -> SimulatedSession:
        duration = persona.session_duration_preference * random.uniform(0.4, 1.5)
        content: Dict[str, int] = {}
        if persona.completion_drive > 0.5:
            content["main_quest"] = random.randint(1, 3)
        if persona.exploration_drive > 0.4:
            content["exploration"] = random.randint(1, 5)
        if persona.completion_drive > 0.7:
            content["collection"] = random.randint(1, 4)
        content["combat"] = random.randint(0, int(persona.skill_level * 8))

        difficulty = 1.0 - persona.skill_level * 0.6 - persona.patience * 0.2
        frustration_events = 0
        outcome = SessionOutcome.ENGAGED
        quit_reason = ""

        base_satisfaction = 0.5
        content_variety = len(content)
        if content_variety >= 3:
            base_satisfaction += 0.15
        elif content_variety == 1:
            base_satisfaction -= 0.1

        difficulty_score = 1.0 - difficulty + persona.skill_level * 0.2
        if difficulty > persona.skill_level + 0.3:
            frustration_events += 1
            base_satisfaction -= 0.2

        if frustration > 0.5:
            frustration_events += random.randint(1, 3)
            base_satisfaction -= 0.3

        if base_satisfaction < 0.2:
            outcome = SessionOutcome.RAGE_QUIT
            quit_reason = "overwhelming difficulty and accumulated frustration"
        elif base_satisfaction < 0.35:
            outcome = SessionOutcome.FRUSTRATED
            quit_reason = "below satisfaction threshold"
        elif base_satisfaction < 0.45:
            outcome = SessionOutcome.BORED
        elif base_satisfaction >= 0.65:
            outcome = SessionOutcome.ENGAGED

        return SimulatedSession(
            persona_id=persona.id,
            game_id=game_id,
            session_number=session_num,
            duration_seconds=round(duration, 1),
            content_consumed=content,
            difficulty_perceived=round(difficulty, 2),
            outcome=outcome,
            satisfaction_score=round(max(0.0, min(1.0, base_satisfaction)), 2),
            frustration_events=frustration_events,
            quit_reason=quit_reason,
        )

    def _create_frustrated_session(self,
                                   persona: PlayerPersona,
                                   game_id: str,
                                   session_num: int) -> SimulatedSession:
        return SimulatedSession(
            persona_id=persona.id,
            game_id=game_id,
            session_number=session_num,
            duration_seconds=random.uniform(30, 180),
            difficulty_perceived=0.95,
            outcome=SessionOutcome.RAGE_QUIT,
            satisfaction_score=0.05,
            frustration_events=random.randint(3, 6),
            quit_reason="cumulative frustration exceeded threshold",
        )

    # ---- Report Generation ----

    def generate_report(self, game_id: str) -> Optional[GameExperienceReport]:
        journeys = self._journeys.get(game_id, {})
        if not journeys:
            return None
        report = GameExperienceReport(game_id=game_id)
        satisfaction_sum = 0.0
        retention_sum = 0.0
        churn_sum = 0.0
        content_frustration: Dict[str, int] = {}
        content_engagement: Dict[str, int] = {}

        for persona_id, journey in journeys.items():
            report.journeys.append(journey)
            satisfaction_sum += journey.net_satisfaction
            retention_sum += journey.estimated_retention_days
            churn_sum += journey.churn_risk

            persona = self._personas.get(persona_id)
            arch_key = persona.archetype.value if persona else "unknown"
            report.archetype_performance[arch_key] = {
                "sessions": journey.total_sessions,
                "playtime": journey.total_playtime,
                "satisfaction": journey.net_satisfaction,
                "churn_risk": journey.churn_risk,
            }

            for session in journey.sessions:
                for cat, count in session.content_consumed.items():
                    if session.outcome in (SessionOutcome.RAGE_QUIT, SessionOutcome.FRUSTRATED):
                        content_frustration[cat] = content_frustration.get(cat, 0) + count
                    if session.outcome == SessionOutcome.ENGAGED:
                        content_engagement[cat] = content_engagement.get(cat, 0) + count

        n = len(journeys)
        report.average_satisfaction = round(satisfaction_sum / n, 2)
        report.average_retention_days = round(retention_sum / n, 1)
        report.overall_churn_risk = round(churn_sum / n, 2)
        report.most_frustrating_content = max(content_frustration, key=content_frustration.get) if content_frustration else "none"
        report.most_engaging_content = max(content_engagement, key=content_engagement.get) if content_engagement else "none"
        report.recommendations = self._generate_recommendations(report)
        self._reports[game_id] = report
        return report

    def _generate_recommendations(self, report: GameExperienceReport) -> List[str]:
        recs: List[str] = []
        if report.overall_churn_risk > 0.5:
            recs.append("High churn risk detected: consider reducing early-game difficulty spikes")
        if report.average_satisfaction < 0.4:
            recs.append("Low satisfaction: increase content variety and reduce repetitive encounters")
        if report.most_frustrating_content != "none":
            recs.append(f"Content category '{report.most_frustrating_content}' causes most frustration: review pacing and difficulty calibration")
        if report.average_retention_days < 7:
            recs.append("Short retention window: add daily rewards and meaningful progression hooks")
        for arch, perf in report.archetype_performance.items():
            if perf.get("churn_risk", 0) > 0.7:
                recs.append(f"Archetype '{arch}' at high risk: ensure content is accessible for this play style")
        return recs

    # ---- Analytics ----

    def get_journey(self,
                    game_id: str,
                    persona_id: str) -> Optional[PlayerJourney]:
        return self._journeys.get(game_id, {}).get(persona_id)

    def get_report(self, game_id: str) -> Optional[GameExperienceReport]:
        return self._reports.get(game_id)

    def compare_archetypes(self,
                           game_id: str) -> Dict[str, Any]:
        journeys = self._journeys.get(game_id, {})
        comparison: Dict[str, Dict[str, Any]] = {}
        for pid, journey in journeys.items():
            persona = self._personas.get(pid)
            arch = persona.archetype.value if persona else "unknown"
            comparison[arch] = {
                "sessions": journey.total_sessions,
                "total_playtime": journey.total_playtime,
                "satisfaction": journey.net_satisfaction,
                "churn_risk": journey.churn_risk,
                "retention_days": journey.estimated_retention_days,
                "frustration_points": len(journey.critical_frustration_points),
            }
        return {
            "game_id": game_id,
            "archetypes": comparison,
            "total_archetypes_compared": len(comparison),
        }

    # ---- Helpers ----

    @staticmethod
    def _calculate_churn_risk(journey: PlayerJourney) -> float:
        if not journey.sessions:
            return 1.0
        negative_outcomes = sum(
            1 for s in journey.sessions
            if s.outcome in (SessionOutcome.RAGE_QUIT, SessionOutcome.FRUSTRATED)
        )
        bored_outcomes = sum(
            1 for s in journey.sessions if s.outcome == SessionOutcome.BORED
        )
        risk = (negative_outcomes * 0.4 + bored_outcomes * 0.15) / len(journey.sessions)
        risk += len(journey.critical_frustration_points) * 0.1
        return round(min(1.0, max(0.0, risk)), 2)

    @staticmethod
    def _calculate_satisfaction(journey: PlayerJourney) -> float:
        if not journey.sessions:
            return 0.0
        scores = [s.satisfaction_score for s in journey.sessions]
        weights = [1.0 - (i * 0.01) for i in range(len(scores))]
        weighted = sum(s * w for s, w in zip(scores, weights))
        return round(weighted / sum(weights), 2)

    @staticmethod
    def _estimate_retention(journey: PlayerJourney) -> int:
        base = max(1, journey.total_sessions * 2)
        streak_bonus = journey.longest_streak * 3
        satisfaction_malus = int((1.0 - journey.net_satisfaction) * 20)
        return max(1, base + streak_bonus - satisfaction_malus)

    def get_stats(self) -> Dict[str, Any]:
        total_journeys = sum(len(v) for v in self._journeys.values())
        total_sessions = sum(
            j.total_sessions
            for journeys in self._journeys.values()
            for j in journeys.values()
        )
        archetype_distribution: Dict[str, int] = {}
        for p in self._personas.values():
            key = p.archetype.value
            archetype_distribution[key] = archetype_distribution.get(key, 0) + 1
        return {
            "total_personas": len(self._personas),
            "archetype_distribution": archetype_distribution,
            "total_journeys": total_journeys,
            "total_simulated_sessions": total_sessions,
            "reports_generated": len(self._reports),
            "preset_archetypes": len(self._ARCHETYPE_PRESETS),
        }


def get_player_modeler() -> PlayerModeler:
    return PlayerModeler.get_instance()