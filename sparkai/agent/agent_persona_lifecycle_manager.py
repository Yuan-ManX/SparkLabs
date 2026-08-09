"""
SparkLabs Agent - Persona Lifecycle Manager"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class LifeStage(Enum):
    """Stages of a persona's lifecycle."""
    GERMINATE = "germinate"
    FORM = "form"
    FLOURISH = "flourish"
    FALTER = "falter"
    LEGACY = "legacy"
    DORMANT = "dormant"   # not yet activated


class LifecyclePhase(Enum):
    """Phases of the lifecycle manager cycle."""
    GERMINATE = "germinate"
    FORM = "form"
    FLOURISH = "flourish"
    FALTER = "falter"
    LEGACY = "legacy"


class LifeEventCategory(Enum):
    """Categories of life events that shape personas."""
    BIRTH = "birth"
    FORMATIVE = "formative"       # childhood, training, early experiences
    ACHIEVEMENT = "achievement"   # successes, recognitions
    RELATIONSHIP = "relationship"  # bonds formed or broken
    LOSS = "loss"                  # death, betrayal, failure
    TRANSFORMATION = "transformation"  # profound change
    CRISIS = "crisis"             # severe challenge
    REDEMPTION = "redemption"     # recovery from faltering
    DEATH = "death"               # end of physical existence
    LEGACY_EVENT = "legacy_event"  # posthumous impact


class TraitDimension(Enum):
    """Personality trait dimensions that evolve over the lifecycle."""
    COURAGE = "courage"
    WISDOM = "wisdom"
    EMPATHY = "empathy"
    AMBITION = "ambition"
    LOYALTY = "loyalty"
    CUNNING = "cunning"
    RESILIENCE = "resilience"
    CHARISMA = "charisma"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class LifeEvent:
    """An event that shaped or will shape a persona."""
    event_id: str
    category: LifeEventCategory
    description: str
    timestamp: float
    # Trait deltas applied by this event (-1.0 to 1.0 per dimension)
    trait_deltas: Dict[str, float] = field(default_factory=dict)
    # Relationships affected
    relationship_changes: Dict[str, int] = field(default_factory=dict)  # target_name -> delta
    # Narrative weight (how story-significant this event is)
    narrative_weight: float = 0.5
    # Stage this event is associated with
    stage_at_event: str = "form"


@dataclass
class LifeScript:
    """A dynamic script that guides a persona's lifecycle."""
    theme: str                   # core life theme (e.g., "redemption", "ambition")
    arc_type: str                # "hero", "tragedy", "comic", "neutral"
    formative_milestones: List[str]  # planned formative events
    flourish_goals: List[str]   # what they pursue at peak
    falter_catalyst: str         # what causes their crisis
    legacy_form: str             # how they are remembered
    # Flexibility: how much the script can deviate from plan (0-1)
    flexibility: float = 0.5
    # Current progress through the script (0-1)
    progress: float = 0.0


@dataclass
class Persona:
    """A tracked NPC persona with full lifecycle state."""
    persona_id: str
    name: str
    archetype: str               # "warrior", "scholar", "rogue", etc.
    stage: LifeStage
    # Current traits (0.0 - 1.0 each)
    traits: Dict[str, float]
    # Life script guiding the arc
    script: LifeScript
    # Relationships: name -> strength (-1.0 enemy to 1.0 ally)
    relationships: Dict[str, float]
    # Life events chronology
    events: List[LifeEvent] = field(default_factory=list)
    # Lifecycle metrics
    age_in_cycles: int = 0
    vitality: float = 1.0        # 0.0 = dead, 1.0 = peak health
    agency: float = 0.5          # how actively they pursue goals
    reputation: float = 0.0      # -1.0 infamy to 1.0 fame
    # Legacy (filled when stage reaches LEGACY)
    legacy_summary: str = ""
    legacy_impact: float = 0.0   # how much they changed the world
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_advanced_at: float = field(default_factory=time.time)
    stage_transitions: int = 0


@dataclass
class LifecycleStats:
    """Aggregate statistics for the lifecycle manager."""
    total_personas_created: int = 0
    total_personas_active: int = 0
    total_personas_in_legacy: int = 0
    total_events_recorded: int = 0
    total_stage_transitions: int = 0
    avg_vitality: float = 0.0
    avg_agency: float = 0.0
    avg_reputation: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Persona Lifecycle Manager
# =============================================================================

class AgentPersonaLifecycleManager:
    """
    Singleton agent that manages the complete lifecycle of NPC personas.

    The manager runs a 5-phase cycle that advances all active personas:
      1. GERMINATE - Seed new personas with traits and life scripts
      2. FORM      - Apply formative events, develop traits and bonds
      3. FLOURISH  - Personas pursue goals at peak agency
      4. FALTER    - Crises challenge personas, testing resilience
      5. LEGACY    - Concluded personas leave enduring impact

    The manager ensures NPCs are not static props but living entities
    whose stories unfold over the course of the game.
    """

    _instance: Optional["AgentPersonaLifecycleManager"] = None
    _instance_lock = threading.Lock()

    # Stage progression thresholds (in age_in_cycles)
    STAGE_DURATIONS: Dict[LifeStage, int] = {
        LifeStage.GERMINATE: 3,
        LifeStage.FORM: 8,
        LifeStage.FLOURISH: 12,
        LifeStage.FALTER: 6,
        LifeStage.LEGACY: 5,  # legacy persists but transitions are done
    }
    # Vitality decay per cycle during FALTER
    FALTER_VITALITY_DECAY = 0.08
    # Minimum vitality to survive a crisis
    CRISIS_SURVIVAL_THRESHOLD = 0.2
    # Agency boost during FLOURISH
    FLOURISH_AGENCY_BOOST = 0.05
    # Reputation change per cycle based on traits
    REPUTATION_TRAIT_INFLUENCE = {
        "charisma": 0.02,
        "courage": 0.01,
        "cunning": -0.01,
    }
    # Relationship decay per cycle if not reinforced
    RELATIONSHIP_DECAY = 0.02
    # Maximum events to keep per persona
    MAX_EVENTS_PER_PERSONA = 50
    # Themes and arcs for script generation
    LIFE_THEMES = [
        "redemption", "ambition", "loyalty", "discovery",
        "sacrifice", "vengeance", "love", "duty",
    ]
    ARC_TYPES = ["hero", "tragedy", "comic", "neutral"]

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._personas: Dict[str, Persona] = {}
        self._stats = LifecycleStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._legacy_registry: Dict[str, Dict[str, Any]] = {}  # posthumous records

    @classmethod
    def get_instance(cls) -> "AgentPersonaLifecycleManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Phase 1: GERMINATE - Seed new personas
    # -------------------------------------------------------------------------

    def create_persona(self, persona_id: str, name: str, archetype: str,
                       initial_traits: Optional[Dict[str, float]] = None,
                       theme: Optional[str] = None,
                       arc_type: Optional[str] = None) -> Dict[str, Any]:
        """Create a new persona with a life script."""
        with self._lock:
            if persona_id in self._personas:
                return {"error": f"Persona already exists: {persona_id}"}
            # Generate or use provided traits
            traits: Dict[str, float] = {}
            for dim in TraitDimension:
                if initial_traits and dim.value in initial_traits:
                    traits[dim.value] = max(0.0, min(1.0, float(initial_traits[dim.value])))
                else:
                    # Generate based on archetype bias
                    traits[dim.value] = self._generate_trait_for_archetype(archetype, dim)
            # Generate life script
            script_theme = theme or random.choice(self.LIFE_THEMES)
            script_arc = arc_type or random.choice(self.ARC_TYPES)
            script = LifeScript(
                theme=script_theme,
                arc_type=script_arc,
                formative_milestones=self._generate_milestones(archetype, script_theme),
                flourish_goals=self._generate_goals(archetype, script_theme),
                falter_catalyst=self._generate_catalyst(script_theme, script_arc),
                legacy_form=self._generate_legacy_form(script_theme, script_arc),
                flexibility=round(random.uniform(0.3, 0.8), 2),
                progress=0.0,
            )
            persona = Persona(
                persona_id=persona_id,
                name=name,
                archetype=archetype,
                stage=LifeStage.GERMINATE,
                traits=traits,
                script=script,
                relationships={},
            )
            # Record birth event
            birth_event = LifeEvent(
                event_id=f"evt_{persona_id}_birth",
                category=LifeEventCategory.BIRTH,
                description=f"{name} was born as a {archetype} with the theme of {script_theme}",
                timestamp=time.time(),
                narrative_weight=0.8,
                stage_at_event="germinate",
            )
            persona.events.append(birth_event)
            self._personas[persona_id] = persona
            self._stats.total_personas_created += 1
            self._stats.total_personas_active += 1
            return self._persona_to_dict(persona)

    def _generate_trait_for_archetype(self, archetype: str,
                                       dim: TraitDimension) -> float:
        """Generate a trait value biased by archetype."""
        # Base random
        base = random.uniform(0.2, 0.8)
        # Archetype biases
        biases = {
            "warrior": {TraitDimension.COURAGE: 0.3, TraitDimension.RESILIENCE: 0.2,
                       TraitDimension.EMPATHY: -0.1},
            "scholar": {TraitDimension.WISDOM: 0.3, TraitDimension.CUNNING: 0.1,
                       TraitDimension.COURAGE: -0.1},
            "rogue": {TraitDimension.CUNNING: 0.3, TraitDimension.CHARISMA: 0.2,
                     TraitDimension.LOYALTY: -0.2},
            "leader": {TraitDimension.CHARISMA: 0.3, TraitDimension.AMBITION: 0.2,
                      TraitDimension.EMPATHY: 0.1},
            "healer": {TraitDimension.EMPATHY: 0.3, TraitDimension.WISDOM: 0.2,
                      TraitDimension.AMBITION: -0.1},
        }
        bias = biases.get(archetype.lower(), {}).get(dim, 0.0)
        return max(0.0, min(1.0, base + bias))

    def _generate_milestones(self, archetype: str, theme: str) -> List[str]:
        """Generate formative milestones for the life script."""
        templates = [
            f"early training in {archetype} arts",
            f"first encounter with {theme}",
            f"mentorship under a master",
            f"first trial of skill",
            f"bond forged with a companion",
        ]
        return random.sample(templates, k=min(3, len(templates)))

    def _generate_goals(self, archetype: str, theme: str) -> List[str]:
        """Generate flourish goals."""
        templates = [
            f"master the {archetype} path",
            f"fulfill the destiny of {theme}",
            f"earn recognition among peers",
            f"protect what matters most",
        ]
        return random.sample(templates, k=min(2, len(templates)))

    def _generate_catalyst(self, theme: str, arc_type: str) -> str:
        """Generate the falter catalyst."""
        if arc_type == "tragedy":
            return f"the {theme} leads to ruin"
        elif arc_type == "hero":
            return f"a supreme test of {theme}"
        elif arc_type == "comic":
            return f"the {theme} is challenged by absurdity"
        return f"the {theme} faces a crossroads"

    def _generate_legacy_form(self, theme: str, arc_type: str) -> str:
        """Generate the legacy form."""
        if arc_type == "tragedy":
            return f"remembered as a cautionary tale of {theme}"
        elif arc_type == "hero":
            return f"celebrated as a paragon of {theme}"
        elif arc_type == "comic":
            return f"fondly recalled for their {theme}"
        return f"noted for their commitment to {theme}"

    def _germinate_phase(self) -> Dict[str, Any]:
        """Advance personas in the GERMINATE stage."""
        advanced = 0
        for persona in self._personas.values():
            if persona.stage != LifeStage.GERMINATE:
                continue
            persona.age_in_cycles += 1
            persona.script.progress = min(1.0, persona.age_in_cycles / 20.0)
            # Check for stage transition
            if persona.age_in_cycles >= self.STAGE_DURATIONS[LifeStage.GERMINATE]:
                self._transition_stage(persona, LifeStage.FORM)
                advanced += 1
        return {"germinating": advanced}

    # -------------------------------------------------------------------------
    # Phase 2: FORM - Apply formative events
    # -------------------------------------------------------------------------

    def record_event(self, persona_id: str, category: str,
                     description: str,
                     trait_deltas: Optional[Dict[str, float]] = None,
                     relationship_changes: Optional[Dict[str, int]] = None,
                     narrative_weight: float = 0.5) -> Dict[str, Any]:
        """Record a life event for a persona."""
        with self._lock:
            persona = self._personas.get(persona_id)
            if persona is None:
                return {"error": f"Persona not found: {persona_id}"}
            try:
                cat = LifeEventCategory(category)
            except ValueError:
                return {"error": f"Invalid category: {category}"}
            event = LifeEvent(
                event_id=f"evt_{persona_id}_{len(persona.events)}",
                category=cat,
                description=description,
                timestamp=time.time(),
                trait_deltas=dict(trait_deltas or {}),
                relationship_changes=dict(relationship_changes or {}),
                narrative_weight=narrative_weight,
                stage_at_event=persona.stage.value,
            )
            self._apply_event(persona, event)
            persona.events.append(event)
            # Trim if too many events
            if len(persona.events) > self.MAX_EVENTS_PER_PERSONA:
                persona.events = persona.events[-self.MAX_EVENTS_PER_PERSONA:]
            self._stats.total_events_recorded += 1
            return self._event_to_dict(event)

    def _apply_event(self, persona: Persona, event: LifeEvent) -> None:
        """Apply an event's effects to a persona."""
        # Apply trait deltas
        for trait, delta in event.trait_deltas.items():
            if trait in persona.traits:
                persona.traits[trait] = max(0.0, min(1.0,
                    persona.traits[trait] + delta))
        # Apply relationship changes
        for target, delta in event.relationship_changes.items():
            current = persona.relationships.get(target, 0.0)
            persona.relationships[target] = max(-1.0, min(1.0,
                current + delta * 0.1))
        # Narrative weight affects agency
        if event.category in (LifeEventCategory.ACHIEVEMENT, LifeEventCategory.REDEMPTION):
            persona.agency = min(1.0, persona.agency + 0.05 * event.narrative_weight)
        elif event.category in (LifeEventCategory.LOSS, LifeEventCategory.CRISIS):
            persona.agency = max(0.0, persona.agency - 0.05 * event.narrative_weight)
            persona.vitality = max(0.0, persona.vitality - 0.05 * event.narrative_weight)

    def _form_phase(self) -> Dict[str, Any]:
        """Advance personas in the FORM stage."""
        advanced = 0
        events_applied = 0
        for persona in self._personas.values():
            if persona.stage != LifeStage.FORM:
                continue
            persona.age_in_cycles += 1
            # Auto-generate formative events based on script milestones
            if persona.age_in_cycles % 2 == 0 and persona.script.formative_milestones:
                milestone_idx = min(len(persona.script.formative_milestones) - 1,
                                    persona.age_in_cycles // 2)
                milestone = persona.script.formative_milestones[milestone_idx]
                event = LifeEvent(
                    event_id=f"evt_{persona.persona_id}_form_{persona.age_in_cycles}",
                    category=LifeEventCategory.FORMATIVE,
                    description=milestone,
                    timestamp=time.time(),
                    trait_deltas=self._generate_formative_deltas(persona),
                    narrative_weight=0.4,
                    stage_at_event="form",
                )
                self._apply_event(persona, event)
                persona.events.append(event)
                events_applied += 1
            # Check for stage transition
            if persona.age_in_cycles >= self.STAGE_DURATIONS[LifeStage.FORM]:
                self._transition_stage(persona, LifeStage.FLOURISH)
                advanced += 1
        return {"formed": advanced, "events_applied": events_applied}

    def _generate_formative_deltas(self, persona: Persona) -> Dict[str, float]:
        """Generate trait deltas for formative events."""
        deltas: Dict[str, float] = {}
        # Pick 1-2 traits to develop
        traits_to_develop = random.sample(list(TraitDimension), k=random.randint(1, 2))
        for dim in traits_to_develop:
            # Formative events usually increase traits
            deltas[dim.value] = round(random.uniform(0.02, 0.08), 3)
        return deltas

    # -------------------------------------------------------------------------
    # Phase 3: FLOURISH - Peak agency
    # -------------------------------------------------------------------------

    def _flourish_phase(self) -> Dict[str, Any]:
        """Advance personas in the FLOURISH stage."""
        advanced = 0
        for persona in self._personas.values():
            if persona.stage != LifeStage.FLOURISH:
                continue
            persona.age_in_cycles += 1
            # Boost agency during flourish
            persona.agency = min(1.0, persona.agency + self.FLOURISH_AGENCY_BOOST)
            # Reputation grows based on traits
            for trait, influence in self.REPUTATION_TRAIT_INFLUENCE.items():
                if trait in persona.traits:
                    persona.reputation = max(-1.0, min(1.0,
                        persona.reputation + persona.traits[trait] * influence * 0.1))
            # Check for stage transition
            if persona.age_in_cycles >= self.STAGE_DURATIONS[LifeStage.FLOURISH]:
                self._transition_stage(persona, LifeStage.FALTER)
                advanced += 1
        return {"flourished": advanced}

    # -------------------------------------------------------------------------
    # Phase 4: FALTER - Crisis and decline
    # -------------------------------------------------------------------------

    def _falter_phase(self) -> Dict[str, Any]:
        """Advance personas in the FALTER stage."""
        advanced = 0
        crises_survived = 0
        crises_failed = 0
        for persona in self._personas.values():
            if persona.stage != LifeStage.FALTER:
                continue
            persona.age_in_cycles += 1
            # Vitality decays during falter
            persona.vitality = max(0.0, persona.vitality - self.FALTER_VITALITY_DECAY)
            # Agency decreases
            persona.agency = max(0.0, persona.agency - 0.03)
            # Resilience determines survival
            resilience = persona.traits.get("resilience", 0.3)
            if persona.vitality <= self.CRISIS_SURVIVAL_THRESHOLD:
                if random.random() < resilience:
                    # Redemption arc
                    persona.vitality = max(0.3, persona.vitality + 0.2)
                    self._record_redemption(persona)
                    crises_survived += 1
                else:
                    # Persona falls
                    crises_failed += 1
                    self._transition_stage(persona, LifeStage.LEGACY)
                    advanced += 1
                    continue
            # Check for stage transition
            if persona.age_in_cycles >= self.STAGE_DURATIONS[LifeStage.FALTER]:
                if persona.vitality > self.CRISIS_SURVIVAL_THRESHOLD:
                    self._transition_stage(persona, LifeStage.LEGACY)
                else:
                    self._transition_stage(persona, LifeStage.LEGACY)
                advanced += 1
        return {
            "faltered": advanced,
            "crises_survived": crises_survived,
            "crises_failed": crises_failed,
        }

    def _record_redemption(self, persona: Persona) -> None:
        """Record a redemption event."""
        event = LifeEvent(
            event_id=f"evt_{persona.persona_id}_redemption",
            category=LifeEventCategory.REDEMPTION,
            description=f"{persona.name} found redemption through {persona.script.theme}",
            timestamp=time.time(),
            trait_deltas={"resilience": 0.1, "wisdom": 0.05},
            narrative_weight=0.9,
            stage_at_event="falter",
        )
        self._apply_event(persona, event)
        persona.events.append(event)

    # -------------------------------------------------------------------------
    # Phase 5: LEGACY - Conclude and leave impact
    # -------------------------------------------------------------------------

    def _legacy_phase(self) -> Dict[str, Any]:
        """Advance personas in the LEGACY stage."""
        concluded = 0
        for persona in self._personas.values():
            if persona.stage != LifeStage.LEGACY:
                continue
            persona.age_in_cycles += 1
            # Generate legacy summary if not done
            if not persona.legacy_summary:
                persona.legacy_summary = self._generate_legacy_summary(persona)
                persona.legacy_impact = self._compute_legacy_impact(persona)
                # Record legacy event
                event = LifeEvent(
                    event_id=f"evt_{persona.persona_id}_legacy",
                    category=LifeEventCategory.LEGACY_EVENT,
                    description=persona.legacy_summary,
                    timestamp=time.time(),
                    narrative_weight=1.0,
                    stage_at_event="legacy",
                )
                persona.events.append(event)
                # Register in legacy registry
                self._legacy_registry[persona.persona_id] = {
                    "name": persona.name,
                    "archetype": persona.archetype,
                    "summary": persona.legacy_summary,
                    "impact": persona.legacy_impact,
                    "reputation": persona.reputation,
                    "theme": persona.script.theme,
                }
                # Move to dormant after legacy is set
                persona.stage = LifeStage.DORMANT
                self._stats.total_personas_in_legacy += 1
                self._stats.total_personas_active -= 1
                concluded += 1
        return {"legacies_concluded": concluded}

    def _generate_legacy_summary(self, persona: Persona) -> str:
        """Generate a legacy summary for a concluded persona."""
        return (f"{persona.name}, a {persona.archetype} whose life was defined by "
                f"{persona.script.theme}, {persona.script.legacy_form}. "
                f"Reputation: {persona.reputation:.2f}, "
                f"Lived through {len(persona.events)} significant events.")

    def _compute_legacy_impact(self, persona: Persona) -> float:
        """Compute the legacy impact score (0-1)."""
        # Based on reputation magnitude, event count, and peak traits
        rep_factor = abs(persona.reputation)
        event_factor = min(1.0, len(persona.events) / 20.0)
        peak_trait = max(persona.traits.values()) if persona.traits else 0.5
        return round((rep_factor * 0.4 + event_factor * 0.3 + peak_trait * 0.3), 3)

    # -------------------------------------------------------------------------
    # Stage Transition
    # -------------------------------------------------------------------------

    def _transition_stage(self, persona: Persona, new_stage: LifeStage) -> None:
        """Transition a persona to a new life stage."""
        old_stage = persona.stage
        persona.stage = new_stage
        persona.stage_transitions += 1
        persona.last_advanced_at = time.time()
        persona.script.progress = min(1.0, persona.script.progress + 0.2)
        self._stats.total_stage_transitions += 1
        logger.debug(f"Persona {persona.name} transitioned: {old_stage.value} -> {new_stage.value}")

    # -------------------------------------------------------------------------
    # Lifecycle Cycle Orchestration
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single lifecycle management cycle.

        Phases: GERMINATE -> FORM -> FLOURISH -> FALTER -> LEGACY
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: GERMINATE
            phase = LifecyclePhase.GERMINATE
            germ_info = self._germinate_phase()

            # Phase 2: FORM
            phase = LifecyclePhase.FORM
            form_info = self._form_phase()

            # Phase 3: FLOURISH
            phase = LifecyclePhase.FLOURISH
            flourish_info = self._flourish_phase()

            # Phase 4: FALTER
            phase = LifecyclePhase.FALTER
            falter_info = self._falter_phase()

            # Phase 5: LEGACY
            phase = LifecyclePhase.LEGACY
            legacy_info = self._legacy_phase()

            # Apply relationship decay
            self._apply_relationship_decay()

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._update_averages()

            self._active = False

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "germinate": germ_info,
                "form": form_info,
                "flourish": flourish_info,
                "falter": falter_info,
                "legacy": legacy_info,
                "total_personas": len(self._personas),
                "active_personas": sum(1 for p in self._personas.values()
                                       if p.stage != LifeStage.DORMANT),
                "legacy_personas": len(self._legacy_registry),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _apply_relationship_decay(self) -> None:
        """Apply decay to all relationships."""
        for persona in self._personas.values():
            for target in list(persona.relationships.keys()):
                persona.relationships[target] *= (1.0 - self.RELATIONSHIP_DECAY)
                # Remove if decayed to near-zero
                if abs(persona.relationships[target]) < 0.01:
                    del persona.relationships[target]

    def _update_averages(self) -> None:
        """Update average statistics."""
        active = [p for p in self._personas.values() if p.stage != LifeStage.DORMANT]
        if not active:
            self._stats.avg_vitality = 0.0
            self._stats.avg_agency = 0.0
            self._stats.avg_reputation = 0.0
            return
        self._stats.avg_vitality = round(
            sum(p.vitality for p in active) / len(active), 3)
        self._stats.avg_agency = round(
            sum(p.agency for p in active) / len(active), 3)
        self._stats.avg_reputation = round(
            sum(p.reputation for p in active) / len(active), 3)

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple lifecycle cycles with synthetic personas."""
        with self._lock:
            # Seed personas if empty
            if not self._personas:
                self._seed_synthetic_personas()
            results = []
            for _ in range(max(1, cycles)):
                results.append(self.run_cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_stats": self._stats_to_dict(),
            }

    def _seed_synthetic_personas(self) -> None:
        """Seed synthetic personas for simulation."""
        archetypes = ["warrior", "scholar", "rogue", "leader", "healer"]
        names = ["Aria", "Kael", "Lyra", "Thorne", "Mira", "Darin", "Sela", "Ryn"]
        for i in range(6):
            self.create_persona(
                persona_id=f"npc_{i}",
                name=names[i % len(names)],
                archetype=archetypes[i % len(archetypes)],
            )

    # -------------------------------------------------------------------------
    # Query and Inspection
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_personas": len(self._personas),
                "active_personas": sum(1 for p in self._personas.values()
                                       if p.stage != LifeStage.DORMANT),
                "legacy_count": len(self._legacy_registry),
                "stats": self._stats_to_dict(),
            }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_personas_created": self._stats.total_personas_created,
            "total_personas_active": self._stats.total_personas_active,
            "total_personas_in_legacy": self._stats.total_personas_in_legacy,
            "total_events_recorded": self._stats.total_events_recorded,
            "total_stage_transitions": self._stats.total_stage_transitions,
            "avg_vitality": self._stats.avg_vitality,
            "avg_agency": self._stats.avg_agency,
            "avg_reputation": self._stats.avg_reputation,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def list_personas(self, stage: Optional[str] = None,
                      limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for persona in self._personas.values():
                if stage and persona.stage.value != stage:
                    continue
                results.append(self._persona_to_dict(persona))
            # Sort by last advanced
            results.sort(key=lambda p: p.get("last_advanced_at", 0), reverse=True)
            return results[:limit]

    def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            persona = self._personas.get(persona_id)
            return self._persona_to_dict(persona) if persona else None

    def list_events(self, persona_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            persona = self._personas.get(persona_id)
            if persona is None:
                return []
            events = sorted(persona.events, key=lambda e: e.timestamp, reverse=True)
            return [self._event_to_dict(e) for e in events[:limit]]

    def list_legacies(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._legacy_registry.values())[:limit]

    def add_relationship(self, persona_id: str, target_name: str,
                         strength: float) -> Dict[str, Any]:
        """Add or update a relationship for a persona."""
        with self._lock:
            persona = self._personas.get(persona_id)
            if persona is None:
                return {"error": f"Persona not found: {persona_id}"}
            s = max(-1.0, min(1.0, float(strength)))
            persona.relationships[target_name] = s
            return {"persona_id": persona_id, "target": target_name, "strength": s}

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            count = len(self._personas)
            self._personas.clear()
            self._legacy_registry.clear()
            self._stats = LifecycleStats()
            self._cycle_count = 0
            return {"reset": True, "cleared_personas": count}

    # -------------------------------------------------------------------------
    # Serialization helpers
    # -------------------------------------------------------------------------

    def _persona_to_dict(self, p: Persona) -> Dict[str, Any]:
        return {
            "persona_id": p.persona_id,
            "name": p.name,
            "archetype": p.archetype,
            "stage": p.stage.value,
            "traits": {k: round(v, 3) for k, v in p.traits.items()},
            "script": {
                "theme": p.script.theme,
                "arc_type": p.script.arc_type,
                "formative_milestones": p.script.formative_milestones,
                "flourish_goals": p.script.flourish_goals,
                "falter_catalyst": p.script.falter_catalyst,
                "legacy_form": p.script.legacy_form,
                "flexibility": p.script.flexibility,
                "progress": round(p.script.progress, 3),
            },
            "relationships": {k: round(v, 3) for k, v in p.relationships.items()},
            "events_count": len(p.events),
            "age_in_cycles": p.age_in_cycles,
            "vitality": round(p.vitality, 3),
            "agency": round(p.agency, 3),
            "reputation": round(p.reputation, 3),
            "legacy_summary": p.legacy_summary,
            "legacy_impact": p.legacy_impact,
            "created_at": p.created_at,
            "last_advanced_at": p.last_advanced_at,
            "stage_transitions": p.stage_transitions,
        }

    def _event_to_dict(self, e: LifeEvent) -> Dict[str, Any]:
        return {
            "event_id": e.event_id,
            "category": e.category.value,
            "description": e.description,
            "timestamp": e.timestamp,
            "trait_deltas": {k: round(v, 3) for k, v in e.trait_deltas.items()},
            "relationship_changes": e.relationship_changes,
            "narrative_weight": round(e.narrative_weight, 3),
            "stage_at_event": e.stage_at_event,
        }
