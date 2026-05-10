"""
SparkLabs Agent - Tutorial Design Engine

Adaptive tutorial content generation for game mechanics onboarding.
Creates context-sensitive, progressively complex tutorial sequences
that respond to player behavior, ensuring mechanics are introduced
at the optimal moment with appropriate scaffolding.

Architecture:
  TutorialDesignEngine
    |-- MechanicsCatalog (structured game mechanic definitions)
    |-- TutorialSequencer (dependency-aware ordering of lessons)
    |-- ScaffoldingGenerator (progressive hint and guidance tiers)
    |-- ComprehensionValidator (player understanding assessment)
    |-- AdaptivePacer (pace adjustment based on player performance)

Scaffolding Tiers:
  - DISCOVERY: minimal guidance, encourage exploration
  - GUIDED: contextual hints and optional prompts
  - DIRECTED: explicit step-by-step instruction
  - PRACTICE: repeated exercises with feedback loops
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ScaffoldingTier(Enum):
    DISCOVERY = "discovery"
    GUIDED = "guided"
    DIRECTED = "directed"
    PRACTICE = "practice"


class TutorialMoment(Enum):
    ON_UNLOCK = "on_unlock"
    ON_FIRST_ENCOUNTER = "on_first_encounter"
    ON_STRUGGLE = "on_struggle"
    ON_REQUEST = "on_request"
    ON_CONTEXT = "on_context"


@dataclass
class MechanicDefinition:
    mechanic_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    complexity: int = 1
    prerequisites: List[str] = field(default_factory=list)
    input_actions: List[str] = field(default_factory=list)
    objective_description: str = ""
    success_criteria: str = ""
    tips: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)


@dataclass
class TutorialStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    order: int = 0
    instruction: str = ""
    highlight_target: str = ""
    input_required: str = ""
    wait_for_completion: bool = True
    timeout_seconds: float = 30.0
    tier: ScaffoldingTier = ScaffoldingTier.GUIDED


@dataclass
class TutorialSequence:
    sequence_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mechanic_id: str = ""
    title: str = ""
    moment: TutorialMoment = TutorialMoment.ON_UNLOCK
    tier: ScaffoldingTier = ScaffoldingTier.GUIDED
    steps: List[TutorialStep] = field(default_factory=list)
    completion_count: int = 0
    skip_count: int = 0
    avg_completion_time: float = 0.0
    is_active: bool = False


@dataclass
class PlayerProgress:
    completed_mechanics: List[str] = field(default_factory=list)
    current_struggle: Optional[str] = None
    struggle_duration: float = 0.0
    tutorial_skips: int = 0
    preferred_tier: ScaffoldingTier = ScaffoldingTier.GUIDED


class TutorialDesignEngine:
    _instance: Optional[TutorialDesignEngine] = None

    def __init__(self):
        self._mechanics: Dict[str, MechanicDefinition] = {}
        self._sequences: Dict[str, TutorialSequence] = {}
        self._player_progress: PlayerProgress = PlayerProgress()
        self._design_count: int = 0

    @classmethod
    def get_instance(cls) -> TutorialDesignEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def define_mechanic(self, mechanic: MechanicDefinition) -> str:
        self._mechanics[mechanic.mechanic_id] = mechanic
        return mechanic.mechanic_id

    def design_tutorial(
        self,
        mechanic_id: str,
        tier: ScaffoldingTier = ScaffoldingTier.GUIDED,
        moment: TutorialMoment = TutorialMoment.ON_UNLOCK,
    ) -> Optional[TutorialSequence]:
        mechanic = self._mechanics.get(mechanic_id)
        if mechanic is None:
            return None

        sequence = TutorialSequence(
            mechanic_id=mechanic_id,
            title=f"Learning: {mechanic.name}",
            moment=moment,
            tier=tier,
        )

        steps = self._generate_steps(mechanic, tier)
        for i, step in enumerate(steps):
            step.order = i
            step.tier = tier
        sequence.steps = steps
        self._sequences[sequence.sequence_id] = sequence
        self._design_count += 1
        return sequence

    def _generate_steps(
        self, mechanic: MechanicDefinition, tier: ScaffoldingTier
    ) -> List[TutorialStep]:
        steps = []

        if tier == ScaffoldingTier.DISCOVERY:
            steps.append(TutorialStep(
                instruction=f"Try using {mechanic.name} - {mechanic.objective_description}",
                tier=tier,
                timeout_seconds=60.0,
            ))
            return steps

        steps.append(TutorialStep(
            instruction=f"Welcome! Let's learn about {mechanic.name}.",
            highlight_target=mechanic.name,
            tier=tier,
        ))

        if mechanic.input_actions:
            steps.append(TutorialStep(
                instruction=f"Press {', '.join(mechanic.input_actions[:2])} to activate.",
                input_required=mechanic.input_actions[0] if mechanic.input_actions else "",
                tier=tier,
            ))

        steps.append(TutorialStep(
            instruction=mechanic.objective_description or f"Try using {mechanic.name} now.",
            tier=tier,
            timeout_seconds=45.0,
        ))

        if tier in (ScaffoldingTier.DIRECTED, ScaffoldingTier.PRACTICE):
            tips_step = TutorialStep(
                instruction="Tips: " + "; ".join(mechanic.tips[:3]) if mechanic.tips else "",
                tier=tier,
            )
            steps.append(tips_step)

            if tier == ScaffoldingTier.PRACTICE:
                steps.append(TutorialStep(
                    instruction="Practice makes perfect! Try again to build muscle memory.",
                    tier=tier,
                    timeout_seconds=60.0,
                ))

        return steps

    def get_tutorial_for_mechanic(self, mechanic_id: str) -> Optional[TutorialSequence]:
        for seq in self._sequences.values():
            if seq.mechanic_id == mechanic_id:
                return seq
        return None

    def record_completion(self, sequence_id: str, completion_time: float = 0.0):
        seq = self._sequences.get(sequence_id)
        if seq:
            seq.completion_count += 1
            if completion_time > 0:
                if seq.avg_completion_time == 0:
                    seq.avg_completion_time = completion_time
                else:
                    seq.avg_completion_time = 0.8 * seq.avg_completion_time + 0.2 * completion_time

    def record_skip(self, sequence_id: str):
        seq = self._sequences.get(sequence_id)
        if seq:
            seq.skip_count += 1
            self._player_progress.tutorial_skips += 1

    def adjust_tier(self, mechanic_id: str) -> ScaffoldingTier:
        seq = self.get_tutorial_for_mechanic(mechanic_id)
        if seq is None:
            return ScaffoldingTier.GUIDED

        skip_ratio = seq.skip_count / max(1, seq.completion_count + seq.skip_count)
        if skip_ratio > 0.5:
            return ScaffoldingTier.DISCOVERY
        elif skip_ratio > 0.2:
            return ScaffoldingTier.GUIDED
        else:
            return ScaffoldingTier.DIRECTED

    def get_next_recommended_tutorial(self) -> Optional[MechanicDefinition]:
        completed = set(self._player_progress.completed_mechanics)
        for mechanic in self._mechanics.values():
            if mechanic.mechanic_id in completed:
                continue
            prereqs_met = all(p in completed for p in mechanic.prerequisites)
            if prereqs_met:
                return mechanic
        return None

    def get_all_mechanics_ordered(self) -> List[MechanicDefinition]:
        ordered = []
        visited = set()

        def visit(mechanic_id: str):
            if mechanic_id in visited:
                return
            mechanic = self._mechanics.get(mechanic_id)
            if mechanic is None:
                return
            visited.add(mechanic_id)
            for prereq in mechanic.prerequisites:
                visit(prereq)
            ordered.append(mechanic)

        for mid in self._mechanics:
            visit(mid)
        return ordered

    def get_stats(self) -> Dict[str, Any]:
        total_steps = sum(len(s.steps) for s in self._sequences.values())
        return {
            "mechanics_defined": len(self._mechanics),
            "tutorials_designed": self._design_count,
            "total_sequences": len(self._sequences),
            "total_steps": total_steps,
            "preferred_tier": self._player_progress.preferred_tier.value,
            "tutorial_skips": self._player_progress.tutorial_skips,
        }


def get_tutorial_designer() -> TutorialDesignEngine:
    return TutorialDesignEngine.get_instance()