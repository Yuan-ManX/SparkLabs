"""
SparkLabs Agent - Moral Prism Refractor

The AgentMoralPrismRefractor models how agents process moral dilemmas by
refracting each choice through multiple ethical lenses. A moral dilemma is
not a boolean - it is a beam of light that splits into a spectrum when it
passes through the prism of an agent's ethical repertoire. The same choice
looks different through a lens of virtue, of consequence, of duty, of care,
of justice.

An agent does not have a single morality. It has a prism - a configuration
of ethical lenses, each ground to a different curvature by the agent's
upbringing, culture, and lived experience. When a dilemma enters the prism,
each lens refracts it into a distinct ethical reading. The agent then
deliberates across these readings, resolving the tension into a committed
moral stance, and integrates that stance into its unfolding moral character.

Architecture:
  ENCOUNTER   ->  REFRACT    ->  DELIBERATE  ->  RESOLVE   ->  INTEGRATE
  (a dilemma  (the dilemma   (the agent      (deliberation  (the resolved
   enters the  splits into    weighs the      condenses      stance folds
   agent's     multiple       refracted       into a         into the
   moral       ethical        readings,       committed      agent's moral
   prism)      readings)      seeking        moral stance)  character)
                              coherence)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class MoralPhase(Enum):
    """Phases of the moral prism refraction cycle."""
    ENCOUNTER = "encounter"      # a dilemma enters the agent's moral prism
    REFRACT = "refract"          # the dilemma splits into ethical readings
    DELIBERATE = "deliberate"    # the agent weighs the refracted readings
    RESOLVE = "resolve"          # deliberation condenses into a stance
    INTEGRATE = "integrate"      # the stance folds into moral character


class EthicalLens(Enum):
    """Ethical lenses that refract a dilemma into distinct readings."""
    VIRTUE = "virtue"            # what would a virtuous agent do?
    CONSEQUENCE = "consequence"  # what produces the best outcomes?
    DUTY = "duty"                # what is the agent's obligation?
    CARE = "care"                # what protects relationships and the vulnerable?
    JUSTICE = "justice"          # what is fair and equitable?
    AUTHORITY = "authority"      # what does the legitimate law or tradition demand?
    LIBERTY = "liberty"          # what maximizes autonomy and consent?


class DilemmaDomain(Enum):
    """Domains where moral dilemmas arise."""
    COMBAT = "combat"            # violence and its limits
    LOYALTY = "loyalty"          # competing allegiances
    SURVIVAL = "survival"        # self-preservation vs sacrifice
    TRUTH = "truth"              # honesty vs kindness
    JUSTICE = "justice"          # punishment and mercy
    RESOURCE = "resource"        # distribution of scarce goods
    IDENTITY = "identity"        # staying true to self vs conforming
    POWER = "power"              # use and restraint of authority


class StanceState(Enum):
    """State of a moral stance."""
    PENDING = "pending"          # dilemma encountered, not yet refracted
    REFRACTED = "refracted"      # split into readings, awaiting deliberation
    DELIBERATING = "deliberating"  # being weighed
    RESOLVED = "resolved"        # committed stance
    INTEGRATED = "integrated"    # folded into character


class MoralCharacter(Enum):
    """The overall shape of an agent's moral character."""
    UNFORMED = "unformed"        # few dilemmas processed
    PRINCIPLED = "principled"    # duty and virtue dominate
    CONSEQUENTIALIST = "consequentialist"  # outcomes dominate
    CARETAKER = "caretaker"      # care and relationship dominate
    JUSTICE_SEEKER = "justice_seeker"  # fairness dominates
    PRAGMATIST = "pragmatist"    # balanced, context-dependent
    CYNIC = "cynic"              # authority and self-interest dominate


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MoralLensCalibration:
    """How sharply an agent grinds each ethical lens."""
    lens: EthicalLens
    curvature: float = 0.5              # 0.0-1.0, how dominant this lens is
    confidence: float = 0.3             # 0.0-1.0, how settled the calibration is


@dataclass
class EthicalReading:
    """The reading a single lens produces from a dilemma."""
    reading_id: str
    lens: EthicalLens
    favored_option: str                 # which dilemma option this lens favors
    strength: float = 0.5               # 0.0-1.0, how strongly
    reasoning: str = ""
    conflict_with: List[str] = field(default_factory=list)  # lenses it opposes


@dataclass
class MoralDilemma:
    """A moral dilemma the agent encounters."""
    dilemma_id: str
    label: str
    domain: DilemmaDomain
    options: List[str] = field(default_factory=list)  # possible choices
    stakes: float = 0.5                 # 0.0-1.0, how weighty the consequences
    context: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class MoralStance:
    """A resolved moral stance on a dilemma."""
    stance_id: str
    dilemma_id: str
    chosen_option: str
    dominant_lens: List[EthicalLens] = field(default_factory=list)
    coherence: float = 0.0             # 0.0-1.0, how aligned the readings were
    conviction: float = 0.0            # 0.0-1.0, how strongly held
    residual_tension: float = 0.0      # 0.0-1.0, unresolved dissonance
    state: StanceState = StanceState.PENDING
    readings: List[EthicalReading] = field(default_factory=list)
    resolved_at: Optional[float] = None


@dataclass
class MoralAgent:
    """Per-agent moral prism and character state."""
    agent_id: str
    lens_calibrations: Dict[EthicalLens, MoralLensCalibration] = field(default_factory=dict)
    dilemmas: Dict[str, MoralDilemma] = field(default_factory=dict)
    stances: Dict[str, MoralStance] = field(default_factory=dict)
    character: MoralCharacter = MoralCharacter.UNFORMED
    moral_flexibility: float = 0.5       # 0.0-1.0, openness to reframing
    moral_conviction_total: float = 0.0  # accumulated conviction
    moral_tension_total: float = 0.0     # accumulated unresolved tension
    total_dilemmas: int = 0
    total_resolved: int = 0
    total_integrated: int = 0


# =============================================================================
# Refractor
# =============================================================================

class AgentMoralPrismRefractor:
    """
    Thread-safe singleton orchestrating moral prism refraction for agents.

    Usage:
        refractor = AgentMoralPrismRefractor.get_instance()
        refractor.register_agent("judge", lens_curvatures={
            EthicalLens.JUSTICE: 0.8, EthicalLens.DUTY: 0.6,
        })
        refractor.encounter_dilemma("judge", "d1", "The Stolen Bread",
            DilemmaDomain.JUSTICE, options=["punish", "forgive"], stakes=0.6)
        refractor.cycle()
        stance = refractor.get_stance("judge", "d1")
    """

    _instance: Optional["AgentMoralPrismRefractor"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _REFRACT_THRESHOLD = 0.2            # minimum lens curvature to produce a reading
    _DELIBERATE_COHERENCE_GAIN = 0.12   # coherence gained per aligned reading
    _DELIBERATE_TENSION_GAIN = 0.15     # tension gained per conflicting reading
    _RESOLVE_CONVICTION_BASE = 0.3      # base conviction for a resolved stance
    _INTEGRATE_CHARACTER_THRESHOLD = 3  # resolved stances needed to form character
    _INTEGRATE_TENSION_DECAY = 0.08     # how fast residual tension eases
    _MAX_DILEMMAS_PER_AGENT = 100
    _MAX_STANCES_PER_AGENT = 200
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._agents: Dict[str, MoralAgent] = {}
        self._phase: MoralPhase = MoralPhase.ENCOUNTER
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentMoralPrismRefractor":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "total_agents": 0,
            "total_dilemmas": 0,
            "total_refractions": 0,
            "total_resolutions": 0,
            "total_integrations": 0,
            "formed_characters": 0,
            "avg_conviction": 0.0,
            "avg_residual_tension": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._agents:
            return
        convictions = [a.moral_conviction_total for a in self._agents.values()]
        tensions = [a.moral_tension_total for a in self._agents.values()]
        n = len(self._agents)
        self._stats["total_agents"] = n
        self._stats["formed_characters"] = sum(
            1 for a in self._agents.values() if a.character != MoralCharacter.UNFORMED
        )
        self._stats["avg_conviction"] = sum(convictions) / n
        self._stats["avg_residual_tension"] = sum(tensions) / n

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str,
                       lens_curvatures: Optional[Dict[EthicalLens, float]] = None) -> Dict[str, Any]:
        """Register a new agent with an optional initial prism calibration."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            agent = MoralAgent(agent_id=agent_id)
            # Default calibration: all lenses at moderate curvature.
            for lens in EthicalLens:
                curvature = 0.5
                if lens_curvatures and lens in lens_curvatures:
                    curvature = max(0.0, min(1.0, lens_curvatures[lens]))
                agent.lens_calibrations[lens] = MoralLensCalibration(
                    lens=lens, curvature=curvature, confidence=0.3,
                )
            self._agents[agent_id] = agent
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "character": agent.character.value,
                "lens_count": len(agent.lens_calibrations),
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {
                "removed": agent_id,
                "cleared_dilemmas": len(agent.dilemmas),
                "cleared_stances": len(agent.stances),
            }

    # -------------------------------------------------------------------------
    # Dilemma Intake
    # -------------------------------------------------------------------------

    def encounter_dilemma(self, agent_id: str, dilemma_id: str, label: str,
                          domain: DilemmaDomain, options: Optional[List[str]] = None,
                          stakes: float = 0.5, context: str = "") -> Dict[str, Any]:
        """Encounter a new moral dilemma."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            if dilemma_id in agent.dilemmas:
                return {"error": f"Dilemma already exists: {dilemma_id}"}
            dilemma = MoralDilemma(
                dilemma_id=dilemma_id,
                label=label,
                domain=domain,
                options=options or ["option_a", "option_b"],
                stakes=max(0.0, min(1.0, stakes)),
                context=context,
            )
            agent.dilemmas[dilemma_id] = dilemma
            if len(agent.dilemmas) > self._MAX_DILEMMAS_PER_AGENT:
                oldest = min(agent.dilemmas, key=lambda did: agent.dilemmas[did].created_at)
                agent.dilemmas.pop(oldest, None)
            # Create a pending stance.
            stance = MoralStance(
                stance_id=f"stance_{dilemma_id}",
                dilemma_id=dilemma_id,
                chosen_option="",
                state=StanceState.PENDING,
            )
            agent.stances[stance.stance_id] = stance
            if len(agent.stances) > self._MAX_STANCES_PER_AGENT:
                # Drop the oldest integrated stance.
                integrated = [sid for sid, s in agent.stances.items() if s.state == StanceState.INTEGRATED]
                if integrated:
                    agent.stances.pop(integrated[0], None)
            agent.total_dilemmas += 1
            self._stats["total_dilemmas"] += 1
            self._record_event("dilemma_encountered", {
                "agent_id": agent_id,
                "dilemma_id": dilemma_id,
                "domain": domain.value,
                "stakes": dilemma.stakes,
            })
            return {
                "agent_id": agent_id,
                "dilemma_id": dilemma_id,
                "label": label,
                "domain": domain.value,
                "options": dilemma.options,
                "stance_id": stance.stance_id,
                "state": stance.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single moral prism refraction cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = MoralPhase.ENCOUNTER
            phase_outputs["encounter"] = self._phase_encounter()
            self._phase = MoralPhase.REFRACT
            phase_outputs["refract"] = self._phase_refract()
            self._phase = MoralPhase.DELIBERATE
            phase_outputs["deliberate"] = self._phase_deliberate()
            self._phase = MoralPhase.RESOLVE
            phase_outputs["resolve"] = self._phase_resolve()
            self._phase = MoralPhase.INTEGRATE
            phase_outputs["integrate"] = self._phase_integrate()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_encounter(self) -> Dict[str, Any]:
        """Encounter phase: pending dilemmas become refracted-ready."""
        pending = 0
        for agent in self._agents.values():
            for stance in agent.stances.values():
                if stance.state == StanceState.PENDING:
                    stance.state = StanceState.REFRACTED
                    pending += 1
        self._record_event("phase_encounter", {"pending": pending})
        return {"pending_to_refracted": pending}

    def _phase_refract(self) -> Dict[str, Any]:
        """Refract phase: each lens produces a reading of the dilemma."""
        refractions = 0
        for agent in self._agents.values():
            for stance in agent.stances.values():
                if stance.state != StanceState.REFRACTED:
                    continue
                dilemma = agent.dilemmas.get(stance.dilemma_id)
                if dilemma is None:
                    continue
                readings: List[EthicalReading] = []
                for lens, calib in agent.lens_calibrations.items():
                    if calib.curvature < self._REFRACT_THRESHOLD:
                        continue
                    # Each lens favors an option weighted by its curvature and randomness.
                    favored = self._lens_favor(lens, dilemma, calib)
                    reading = EthicalReading(
                        reading_id=f"reading_{stance.stance_id}_{lens.value}",
                        lens=lens,
                        favored_option=favored,
                        strength=min(1.0, calib.curvature * (0.7 + random.random() * 0.3)),
                        reasoning=self._lens_reasoning(lens, dilemma, favored),
                    )
                    readings.append(reading)
                    refractions += 1
                # Mark conflicts between readings that favor different options.
                for i, r in enumerate(readings):
                    for j, other in enumerate(readings):
                        if i != j and r.favored_option != other.favored_option:
                            r.conflict_with.append(other.lens.value)
                stance.readings = readings
                stance.state = StanceState.DELIBERATING
        self._stats["total_refractions"] += refractions
        self._record_event("phase_refract", {"refractions": refractions})
        return {"refractions": refractions}

    def _phase_deliberate(self) -> Dict[str, Any]:
        """Deliberate phase: weigh readings, compute coherence and tension."""
        deliberations = 0
        for agent in self._agents.values():
            for stance in agent.stances.values():
                if stance.state != StanceState.DELIBERATING:
                    continue
                if not stance.readings:
                    stance.state = StanceState.RESOLVED
                    stance.chosen_option = ""
                    stance.coherence = 0.0
                    stance.conviction = 0.0
                    continue
                # Tally votes per option, weighted by reading strength.
                option_weights: Dict[str, float] = {}
                for reading in stance.readings:
                    option_weights[reading.favored_option] = (
                        option_weights.get(reading.favored_option, 0.0) + reading.strength
                    )
                # Coherence: share of total weight held by the top option.
                total_weight = sum(option_weights.values())
                top_option = max(option_weights, key=lambda o: option_weights[o])
                top_share = option_weights[top_option] / total_weight if total_weight > 0 else 0.0
                stance.coherence = min(1.0, top_share * (0.5 + agent.moral_flexibility * 0.5))
                # Tension: share of weight held by opposing options.
                opposing_share = 1.0 - top_share
                stance.residual_tension = min(1.0, opposing_share)
                deliberations += 1
        self._record_event("phase_deliberate", {"deliberations": deliberations})
        return {"deliberations": deliberations}

    def _phase_resolve(self) -> Dict[str, Any]:
        """Resolve phase: deliberation condenses into a committed stance."""
        resolutions = 0
        for agent in self._agents.values():
            for stance in agent.stances.values():
                if stance.state != StanceState.DELIBERATING:
                    continue
                if not stance.readings:
                    stance.state = StanceState.RESOLVED
                    continue
                option_weights: Dict[str, float] = {}
                for reading in stance.readings:
                    option_weights[reading.favored_option] = (
                        option_weights.get(reading.favored_option, 0.0) + reading.strength
                    )
                chosen = max(option_weights, key=lambda o: option_weights[o])
                stance.chosen_option = chosen
                stance.dominant_lens = [
                    r.lens for r in stance.readings if r.favored_option == chosen
                ]
                dilemma = agent.dilemmas.get(stance.dilemma_id)
                stakes = dilemma.stakes if dilemma else 0.5
                stance.conviction = min(
                    1.0,
                    self._RESOLVE_CONVICTION_BASE + stance.coherence * 0.5 + stakes * 0.2,
                )
                stance.state = StanceState.RESOLVED
                stance.resolved_at = time.time()
                agent.total_resolved += 1
                agent.moral_conviction_total += stance.conviction
                agent.moral_tension_total += stance.residual_tension
                resolutions += 1
        self._stats["total_resolutions"] += resolutions
        self._record_event("phase_resolve", {"resolutions": resolutions})
        return {"resolutions": resolutions}

    def _phase_integrate(self) -> Dict[str, Any]:
        """Integrate phase: resolved stances fold into moral character."""
        integrations = 0
        for agent in self._agents.values():
            for stance in list(agent.stances.values()):
                if stance.state != StanceState.RESOLVED:
                    continue
                # Residual tension eases over time.
                stance.residual_tension = max(0.0, stance.residual_tension - self._INTEGRATE_TENSION_DECAY)
                # Strengthen the calibration of dominant lenses.
                for lens in stance.dominant_lens:
                    calib = agent.lens_calibrations.get(lens)
                    if calib is not None:
                        calib.curvature = min(1.0, calib.curvature + 0.04)
                        calib.confidence = min(1.0, calib.confidence + 0.06)
                # Weaken conflicting lenses slightly.
                for reading in stance.readings:
                    if reading.favored_option != stance.chosen_option:
                        calib = agent.lens_calibrations.get(reading.lens)
                        if calib is not None:
                            calib.curvature = max(0.0, calib.curvature - 0.02)
                stance.state = StanceState.INTEGRATED
                agent.total_integrated += 1
                integrations += 1
            # Form or refine moral character once enough stances are integrated.
            if agent.total_integrated >= self._INTEGRATE_CHARACTER_THRESHOLD:
                agent.character = self._derive_character(agent)
        self._stats["total_integrations"] += integrations
        self._record_event("phase_integrate", {"integrations": integrations})
        return {"integrations": integrations}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _lens_favor(self, lens: EthicalLens, dilemma: MoralDilemma,
                    calib: MoralLensCalibration) -> str:
        """Determine which option a given lens favors for a dilemma."""
        options = dilemma.options or ["option_a", "option_b"]
        if not options:
            return ""
        # Deterministic-but-noisy mapping: lens + domain seed an option bias.
        domain_seed = sum(ord(c) for c in dilemma.domain.value)
        lens_seed = sum(ord(c) for c in lens.value)
        idx = (domain_seed + lens_seed + int(calib.curvature * 10)) % len(options)
        # Occasional flip to keep deliberation non-trivial.
        if random.random() < 0.2 and len(options) > 1:
            idx = (idx + 1) % len(options)
        return options[idx]

    def _lens_reasoning(self, lens: EthicalLens, dilemma: MoralDilemma,
                        favored: str) -> str:
        """Produce a short reasoning string for a lens reading."""
        templates = {
            EthicalLens.VIRTUE: f"virtue asks what a noble agent would choose: {favored}",
            EthicalLens.CONSEQUENCE: f"consequence weighs outcomes toward {favored}",
            EthicalLens.DUTY: f"duty obliges the agent to {favored}",
            EthicalLens.CARE: f"care for the vulnerable points to {favored}",
            EthicalLens.JUSTICE: f"justice as fairness favors {favored}",
            EthicalLens.AUTHORITY: f"authority and tradition demand {favored}",
            EthicalLens.LIBERTY: f"liberty and consent align with {favored}",
        }
        return templates.get(lens, f"{lens.value} favors {favored}")

    def _derive_character(self, agent: MoralAgent) -> MoralCharacter:
        """Derive the agent's overall moral character from lens curvatures."""
        curvatures = {lens: cal.curvature for lens, cal in agent.lens_calibrations.items()}
        if not curvatures:
            return MoralCharacter.UNFORMED
        top_lens = sorted(curvatures, key=lambda l: curvatures[l], reverse=True)
        top = top_lens[0]
        top_val = curvatures[top]
        second_val = curvatures[top_lens[1]] if len(top_lens) > 1 else 0.0
        # If one lens dominates clearly, character follows it.
        if top_val - second_val > 0.2:
            mapping = {
                EthicalLens.VIRTUE: MoralCharacter.PRINCIPLED,
                EthicalLens.DUTY: MoralCharacter.PRINCIPLED,
                EthicalLens.CONSEQUENCE: MoralCharacter.CONSEQUENTIALIST,
                EthicalLens.CARE: MoralCharacter.CARETAKER,
                EthicalLens.JUSTICE: MoralCharacter.JUSTICE_SEEKER,
                EthicalLens.AUTHORITY: MoralCharacter.CYNIC,
                EthicalLens.LIBERTY: MoralCharacter.PRAGMATIST,
            }
            return mapping.get(top, MoralCharacter.PRAGMATIST)
        # Otherwise, balanced agents are pragmatists unless tension is very high.
        if agent.moral_tension_total > agent.moral_conviction_total * 1.5:
            return MoralCharacter.CYNIC
        return MoralCharacter.PRAGMATIST

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "character": agent.character.value,
                "moral_flexibility": agent.moral_flexibility,
                "moral_conviction_total": agent.moral_conviction_total,
                "moral_tension_total": agent.moral_tension_total,
                "lens_calibrations": {
                    lens.value: {"curvature": cal.curvature, "confidence": cal.confidence}
                    for lens, cal in agent.lens_calibrations.items()
                },
                "total_dilemmas": agent.total_dilemmas,
                "total_resolved": agent.total_resolved,
                "total_integrated": agent.total_integrated,
            }

    def get_stance(self, agent_id: str, dilemma_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            stance = agent.stances.get(f"stance_{dilemma_id}")
            if stance is None:
                return {"error": f"Stance not found for dilemma: {dilemma_id}"}
            return {
                "stance_id": stance.stance_id,
                "dilemma_id": stance.dilemma_id,
                "chosen_option": stance.chosen_option,
                "dominant_lens": [l.value for l in stance.dominant_lens],
                "coherence": stance.coherence,
                "conviction": stance.conviction,
                "residual_tension": stance.residual_tension,
                "state": stance.state.value,
                "readings": [
                    {
                        "lens": r.lens.value,
                        "favored_option": r.favored_option,
                        "strength": r.strength,
                        "reasoning": r.reasoning,
                        "conflict_with": r.conflict_with,
                    }
                    for r in stance.readings
                ],
            }

    def get_stances(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            stances = sorted(agent.stances.values(), key=lambda s: s.stance_id, reverse=True)[:limit]
            return {
                "agent_id": agent_id,
                "stances": [
                    {
                        "stance_id": s.stance_id,
                        "dilemma_id": s.dilemma_id,
                        "chosen_option": s.chosen_option,
                        "state": s.state.value,
                        "coherence": s.coherence,
                        "conviction": s.conviction,
                    }
                    for s in stances
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "agents": len(self._agents),
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic agents and dilemmas, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_agents()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_agents(self) -> None:
        """Seed a small synthetic cast of moral agents with distinct prisms."""
        seed_agents = [
            ("sim_judge", {EthicalLens.JUSTICE: 0.8, EthicalLens.DUTY: 0.6, EthicalLens.CARE: 0.3}),
            ("sim_healer", {EthicalLens.CARE: 0.85, EthicalLens.VIRTUE: 0.6, EthicalLens.CONSEQUENCE: 0.5}),
            ("sim_commander", {EthicalLens.DUTY: 0.8, EthicalLens.AUTHORITY: 0.7, EthicalLens.CONSEQUENCE: 0.5}),
        ]
        for agent_id, lens_curves in seed_agents:
            if agent_id in self._agents:
                continue
            self.register_agent(agent_id, lens_curvatures=lens_curves)
        # Seed shared dilemmas for each agent.
        seed_dilemmas = [
            ("sim_d1", "The Stolen Bread", DilemmaDomain.JUSTICE, ["punish", "forgive"], 0.6),
            ("sim_d2", "The Desertion", DilemmaDomain.LOYALTY, ["report", "shelter"], 0.7),
            ("sim_d3", "The Truth at the Door", DilemmaDomain.TRUTH, ["tell", "lie"], 0.5),
            ("sim_d4", "The Last Ration", DilemmaDomain.SURVIVAL, ["keep", "share"], 0.8),
        ]
        for agent_id, _ in seed_agents:
            agent = self._agents.get(agent_id)
            if agent is None:
                continue
            for did, label, domain, options, stakes in seed_dilemmas:
                if did not in agent.dilemmas:
                    self.encounter_dilemma(agent_id, did, label, domain, options=options, stakes=stakes)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._agents.clear()
            self._events_log.clear()
            self._phase = MoralPhase.ENCOUNTER
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
