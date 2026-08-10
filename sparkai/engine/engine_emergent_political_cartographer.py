"""
SparkLabs Engine - Emergent Political Cartographer"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class PoliticalCartographyPhase(Enum):
    """Phases of the political cartography cycle."""
    SURVEY = "survey"            # survey the agent interaction graph
    CLUSTER = "cluster"          # cluster agents into emergent factions
    GRADIENT = "gradient"        # compute power and influence gradients
    TERRITORY = "territory"      # delineate political territories
    RENDER = "render"            # render the political map snapshot


class InteractionKind(Enum):
    """The kind of interaction between two agents."""
    COOPERATIVE = "cooperative"  # agents work together
    COMPETITIVE = "competitive"  # agents oppose one another
    NEUTRAL = "neutral"          # agents interact without strong feeling
    TRIBUTE = "tribute"          # one agent yields resources to another
    DEFENSE = "defense"          # agents stand together against a threat
    RIVALRY = "rivalry"          # agents contest the same prize


class FactionCohesion(Enum):
    """How tightly an emergent faction holds together."""
    TIGHT = "tight"              # strongly bound
    COHESIVE = "cohesive"        # well bound
    LOOSE = "loose"              # weakly bound
    FRAGMENTED = "fragmented"    # barely a faction at all


class PowerDirection(Enum):
    """The direction of a power gradient between two factions."""
    ASCENDING = "ascending"      # the dominant faction is gaining
    STABLE = "stable"            # the gradient is holding
    WANING = "waning"            # the dominant faction is fading
    COLLAPSING = "collapsing"    # the gradient is inverting


class TerritoryState(Enum):
    """State of a delineated political territory."""
    UNCONTESTED = "uncontested"  # one faction holds it cleanly
    CONTESTED = "contested"      # two or more factions actively dispute it
    ANNEXED = "annexed"          # absorbed by a dominant faction
    FLUID = "fluid"              # control shifts every cycle


class CartographyVitality(Enum):
    """The overall vitality of the political landscape."""
    DORMANT = "dormant"          # few agents, few factions
    STIRRING = "stirring"        # agents interacting, factions forming
    ACTIVE = "active"            # healthy faction and territory dynamics
    TURBULENT = "turbulent"      # too many contested territories
    FRACTURED = "fractured"      # factions splintering faster than forming


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AgentInteraction:
    """A single recorded interaction between two agents."""
    interaction_id: str
    source_agent: str
    target_agent: str
    kind: InteractionKind
    weight: float = 0.5              # 0.0-1.0, how strong the interaction is
    affinity: float = 0.0            # -1.0 to 1.0, cooperative vs competitive
    created_at: float = field(default_factory=time.time)


@dataclass
class EmergentFaction:
    """A faction grown bottom-up from the interaction graph."""
    faction_id: str
    members: List[str] = field(default_factory=list)
    cohesion: FactionCohesion = FactionCohesion.LOOSE
    cohesion_score: float = 0.0      # 0.0-1.0
    power: float = 0.0               # 0.0-1.0, raw capability
    influence: float = 0.0           # 0.0-1.0, power weighted by cohesion
    color: str = ""
    formed_at_cycle: int = 0
    note: str = ""


@dataclass
class PowerGradient:
    """A power and influence gradient between two factions."""
    gradient_id: str
    dominant_faction: str
    subordinate_faction: str
    direction: PowerDirection = PowerDirection.STABLE
    magnitude: float = 0.0           # 0.0-1.0, how steep the gradient is
    influence_flow: float = 0.0      # 0.0-1.0, how much influence flows downhill


@dataclass
class PoliticalTerritory:
    """A political territory delineated by the gradient field."""
    territory_id: str
    controlling_faction: str
    contested_by: List[str] = field(default_factory=list)
    state: TerritoryState = TerritoryState.UNCONTESTED
    stability: float = 0.5           # 0.0-1.0
    region_label: str = ""


@dataclass
class PoliticalMapSnapshot:
    """A rendered snapshot of the political map."""
    snapshot_id: str
    factions: List[Dict[str, Any]] = field(default_factory=list)
    gradients: List[Dict[str, Any]] = field(default_factory=list)
    territories: List[Dict[str, Any]] = field(default_factory=list)
    rendered_at: float = field(default_factory=time.time)
    summary: str = ""


# =============================================================================
# Cartographer
# =============================================================================

class EmergentPoliticalCartographer:
    """
    Thread-safe singleton orchestrating emergent political cartography.

    Usage:
        cartographer = EmergentPoliticalCartographer.get_instance()
        cartographer.register_interaction(
            "a1", [{"target_agent": "a2", "kind": "cooperative", "weight": 0.7}]
        )
        cartographer.cycle()
        factions = cartographer.get_factions()
    """

    _instance: Optional["EmergentPoliticalCartographer"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _CLUSTER_AFFINITY_THRESHOLD = 0.2   # affinity needed to bind two agents
    _GRADIENT_MIN_MAGNITUDE = 0.1       # below this, gradient is treated as flat
    _TERRITORY_CONTEST_MARGIN = 0.15    # power gap below which a territory is contested
    _RENDER_MAX_FACTIONS = 12           # factions shown in a snapshot
    _RENDER_MAX_GRADIENTS = 20
    _RENDER_MAX_TERRITORIES = 16
    _VITALITY_TURBULENT_THRESHOLD = 5   # contested territories before turbulent
    _MAX_FACTIONS = 50
    _MAX_INTERACTIONS = 500
    _MAX_GRADIENTS = 100
    _MAX_TERRITORIES = 80
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._interactions: List[AgentInteraction] = []
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._factions: Dict[str, EmergentFaction] = {}
        self._gradients: Dict[str, PowerGradient] = {}
        self._territories: Dict[str, PoliticalTerritory] = {}
        self._latest_snapshot: Optional[PoliticalMapSnapshot] = None
        self._phase: PoliticalCartographyPhase = PoliticalCartographyPhase.SURVEY
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EmergentPoliticalCartographer":
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
            "cycles_completed": 0,
            "uptime_started_at": time.time(),
            "total_agents": 0,
            "total_interactions": 0,
            "total_factions": 0,
            "total_gradients": 0,
            "total_territories": 0,
            "contested_territories": 0,
            "avg_faction_power": 0.0,
            "avg_faction_cohesion": 0.0,
            "vitality": CartographyVitality.DORMANT.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        contested = sum(
            1 for t in self._territories.values()
            if t.state == TerritoryState.CONTESTED
        )
        if self._factions:
            powers = [f.power for f in self._factions.values()]
            cohesions = [f.cohesion_score for f in self._factions.values()]
            self._stats["avg_faction_power"] = sum(powers) / len(powers)
            self._stats["avg_faction_cohesion"] = sum(cohesions) / len(cohesions)
        else:
            self._stats["avg_faction_power"] = 0.0
            self._stats["avg_faction_cohesion"] = 0.0
        self._stats["total_agents"] = len(self._agents)
        self._stats["total_interactions"] = len(self._interactions)
        self._stats["total_factions"] = len(self._factions)
        self._stats["total_gradients"] = len(self._gradients)
        self._stats["total_territories"] = len(self._territories)
        self._stats["contested_territories"] = contested
        self._stats["vitality"] = self._derive_vitality().value

    def _derive_vitality(self) -> CartographyVitality:
        agents = len(self._agents)
        factions = len(self._factions)
        contested = sum(
            1 for t in self._territories.values()
            if t.state == TerritoryState.CONTESTED
        )
        if agents == 0 and factions == 0:
            return CartographyVitality.DORMANT
        if factions == 0:
            return CartographyVitality.STIRRING
        if contested >= self._VITALITY_TURBULENT_THRESHOLD:
            return CartographyVitality.TURBULENT
        # Fractured when average cohesion drops very low despite having factions.
        avg_cohesion = self._stats.get("avg_faction_cohesion", 0.0)
        if factions >= 3 and avg_cohesion < 0.2:
            return CartographyVitality.FRACTURED
        return CartographyVitality.ACTIVE

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Interaction Intake
    # -------------------------------------------------------------------------

    def register_interaction(self, agent_id: str,
                             interactions: List[Dict[str, Any]],
                             affinity: Optional[float] = None) -> Dict[str, Any]:
        """Register an agent's interactions into the political graph."""
        with self._global_lock:
            if agent_id not in self._agents:
                self._agents[agent_id] = {
                    "interactions": [],
                    "affinity": 0.0,
                }
            added = 0
            for entry in interactions:
                target = entry.get("target_agent") or entry.get("target", "")
                if not target or target == agent_id:
                    continue
                kind_str = str(entry.get("kind", "neutral")).lower()
                try:
                    kind = InteractionKind(kind_str)
                except ValueError:
                    kind = InteractionKind.NEUTRAL
                weight = float(entry.get("weight", 0.5))
                weight = max(0.0, min(1.0, weight))
                entry_affinity = (
                    affinity if affinity is not None
                    else self._default_affinity_for_kind(kind)
                )
                entry_affinity = max(-1.0, min(1.0, entry_affinity))
                interaction_id = (
                    f"int_{agent_id}_{target}_{self._cycle_count}_{added}"
                )
                record = AgentInteraction(
                    interaction_id=interaction_id,
                    source_agent=agent_id,
                    target_agent=target,
                    kind=kind,
                    weight=weight,
                    affinity=entry_affinity,
                )
                self._interactions.append(record)
                if target not in self._agents:
                    self._agents[target] = {
                        "interactions": [],
                        "affinity": 0.0,
                    }
                self._agents[agent_id]["interactions"].append(target)
                added += 1
            if affinity is not None:
                self._agents[agent_id]["affinity"] = max(-1.0, min(1.0, affinity))
            if len(self._interactions) > self._MAX_INTERACTIONS:
                self._interactions = self._interactions[-self._MAX_INTERACTIONS:]
            self._record_event("interaction_registered", {
                "agent_id": agent_id,
                "added": added,
                "affinity": affinity,
            })
            return {
                "agent_id": agent_id,
                "interactions_added": added,
                "total_interactions": len(self._interactions),
                "total_agents": len(self._agents),
            }

    def _default_affinity_for_kind(self, kind: InteractionKind) -> float:
        """Default affinity contribution for a given interaction kind."""
        mapping = {
            InteractionKind.COOPERATIVE: 0.5,
            InteractionKind.DEFENSE: 0.6,
            InteractionKind.TRIBUTE: 0.2,
            InteractionKind.NEUTRAL: 0.0,
            InteractionKind.COMPETITIVE: -0.5,
            InteractionKind.RIVALRY: -0.7,
        }
        return mapping.get(kind, 0.0)

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single political cartography cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = PoliticalCartographyPhase.SURVEY
            phase_outputs.append(self._phase_survey())
            self._phase = PoliticalCartographyPhase.CLUSTER
            phase_outputs.append(self._phase_cluster())
            self._phase = PoliticalCartographyPhase.GRADIENT
            phase_outputs.append(self._phase_gradient())
            self._phase = PoliticalCartographyPhase.TERRITORY
            phase_outputs.append(self._phase_territory())
            self._phase = PoliticalCartographyPhase.RENDER
            phase_outputs.append(self._phase_render())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_survey(self) -> Dict[str, Any]:
        """Survey phase: confirm the interaction graph and tally agent edges."""
        surveyed = 0
        agent_edges: Dict[str, int] = {}
        for interaction in self._interactions:
            agent_edges[interaction.source_agent] = (
                agent_edges.get(interaction.source_agent, 0) + 1
            )
            agent_edges[interaction.target_agent] = (
                agent_edges.get(interaction.target_agent, 0) + 1
            )
            surveyed += 1
        for agent_id, edges in agent_edges.items():
            if agent_id in self._agents:
                self._agents[agent_id]["edge_count"] = edges
        self._record_event("phase_survey", {
            "surveyed": surveyed,
            "agents_in_graph": len(self._agents),
        })
        return {
            "phase": PoliticalCartographyPhase.SURVEY.value,
            "interactions_surveyed": surveyed,
            "agents_in_graph": len(self._agents),
        }

    def _phase_cluster(self) -> Dict[str, Any]:
        """Cluster phase: grow emergent factions from affinity edges."""
        # Build an affinity-weighted adjacency among agents.
        affinity_edges: Dict[str, Dict[str, float]] = {}
        for interaction in self._interactions:
            src = interaction.source_agent
            tgt = interaction.target_agent
            score = interaction.affinity * interaction.weight
            affinity_edges.setdefault(src, {})
            affinity_edges.setdefault(tgt, {})
            affinity_edges[src][tgt] = (
                affinity_edges[src].get(tgt, 0.0) + score
            )
            affinity_edges[tgt][src] = (
                affinity_edges[tgt].get(src, 0.0) + score
            )
        # Connected-components clustering over positive-affinity edges.
        visited: set = set()
        components: List[List[str]] = []
        for agent in self._agents:
            if agent in visited:
                continue
            stack = [agent]
            component: List[str] = []
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor, score in affinity_edges.get(current, {}).items():
                    if neighbor in visited:
                        continue
                    if score >= self._CLUSTER_AFFINITY_THRESHOLD:
                        stack.append(neighbor)
            if len(component) >= 2:
                components.append(component)
            elif len(component) == 1:
                # A lone agent with no binding edges is its own one-member faction.
                components.append(component)
        # Form factions from components.
        new_factions: Dict[str, EmergentFaction] = {}
        for idx, component in enumerate(components):
            faction_id = f"fac_{self._cycle_count}_{idx}"
            cohesion_score = self._compute_cohesion(component, affinity_edges)
            power = self._compute_power(component)
            influence = power * (0.4 + cohesion_score * 0.6)
            faction = EmergentFaction(
                faction_id=faction_id,
                members=list(component),
                cohesion=self._classify_cohesion(cohesion_score, len(component)),
                cohesion_score=cohesion_score,
                power=power,
                influence=influence,
                color=self._pick_color(idx),
                formed_at_cycle=self._cycle_count,
                note=self._faction_note(component, cohesion_score),
            )
            new_factions[faction_id] = faction
        # Replace the faction set each cycle so the map reflects the
        # current interaction graph.
        self._factions = new_factions
        if len(self._factions) > self._MAX_FACTIONS:
            # Keep the most powerful factions when over the cap.
            kept = sorted(
                self._factions.values(),
                key=lambda f: f.power,
                reverse=True,
            )[:self._MAX_FACTIONS]
            self._factions = {f.faction_id: f for f in kept}
        self._record_event("phase_cluster", {
            "factions_formed": len(self._factions),
            "components": len(components),
        })
        return {
            "phase": PoliticalCartographyPhase.CLUSTER.value,
            "factions_formed": len(self._factions),
            "total_factions": len(self._factions),
        }

    def _phase_gradient(self) -> Dict[str, Any]:
        """Gradient phase: compute power and influence gradients between factions."""
        self._gradients.clear()
        factions = list(self._factions.values())
        computed = 0
        for i in range(len(factions)):
            for j in range(i + 1, len(factions)):
                a = factions[i]
                b = factions[j]
                gap = a.power - b.power
                magnitude = abs(gap)
                if magnitude < self._GRADIENT_MIN_MAGNITUDE:
                    continue
                if gap >= 0:
                    dominant, subordinate = a, b
                else:
                    dominant, subordinate = b, a
                direction = self._classify_direction(dominant, subordinate)
                gradient = PowerGradient(
                    gradient_id=(
                        f"grad_{dominant.faction_id}_{subordinate.faction_id}"
                        f"_{self._cycle_count}"
                    ),
                    dominant_faction=dominant.faction_id,
                    subordinate_faction=subordinate.faction_id,
                    direction=direction,
                    magnitude=max(0.0, min(1.0, magnitude)),
                    influence_flow=max(
                        0.0, min(1.0, dominant.influence * magnitude)
                    ),
                )
                self._gradients[gradient.gradient_id] = gradient
                computed += 1
                if len(self._gradients) >= self._MAX_GRADIENTS:
                    break
            if len(self._gradients) >= self._MAX_GRADIENTS:
                break
        self._record_event("phase_gradient", {
            "gradients_computed": computed,
        })
        return {
            "phase": PoliticalCartographyPhase.GRADIENT.value,
            "gradients_computed": computed,
            "total_gradients": len(self._gradients),
        }

    def _phase_territory(self) -> Dict[str, Any]:
        """Territory phase: delineate political territories from the gradient field."""
        self._territories.clear()
        factions = sorted(
            self._factions.values(),
            key=lambda f: f.power,
            reverse=True,
        )
        delineated = 0
        for idx, faction in enumerate(factions):
            # Find rivals whose power is within the contest margin.
            rivals = [
                other.faction_id for other in factions
                if other.faction_id != faction.faction_id
                and abs(faction.power - other.power) <= self._TERRITORY_CONTEST_MARGIN
            ]
            if rivals:
                state = TerritoryState.CONTESTED
                stability = max(0.0, 0.5 - len(rivals) * 0.1)
            elif faction.power > 0.7 and idx == 0:
                state = TerritoryState.ANNEXED
                stability = 0.8
            elif faction.power < 0.2:
                state = TerritoryState.FLUID
                stability = 0.2
            else:
                state = TerritoryState.UNCONTESTED
                stability = 0.5 + faction.cohesion_score * 0.3
            territory = PoliticalTerritory(
                territory_id=f"terr_{faction.faction_id}_{self._cycle_count}",
                controlling_faction=faction.faction_id,
                contested_by=rivals,
                state=state,
                stability=max(0.0, min(1.0, stability)),
                region_label=f"region_{idx}",
            )
            self._territories[territory.territory_id] = territory
            delineated += 1
            if len(self._territories) >= self._MAX_TERRITORIES:
                break
        self._record_event("phase_territory", {
            "territories_delineated": delineated,
        })
        return {
            "phase": PoliticalCartographyPhase.TERRITORY.value,
            "territories_delineated": delineated,
            "total_territories": len(self._territories),
        }

    def _phase_render(self) -> Dict[str, Any]:
        """Render phase: produce a political map snapshot."""
        factions_view = [
            self._faction_to_dict(f)
            for f in sorted(
                self._factions.values(),
                key=lambda f: f.power,
                reverse=True,
            )[:self._RENDER_MAX_FACTIONS]
        ]
        gradients_view = [
            {
                "gradient_id": g.gradient_id,
                "dominant_faction": g.dominant_faction,
                "subordinate_faction": g.subordinate_faction,
                "direction": g.direction.value,
                "magnitude": g.magnitude,
                "influence_flow": g.influence_flow,
            }
            for g in sorted(
                self._gradients.values(),
                key=lambda g: g.magnitude,
                reverse=True,
            )[:self._RENDER_MAX_GRADIENTS]
        ]
        territories_view = [
            {
                "territory_id": t.territory_id,
                "controlling_faction": t.controlling_faction,
                "contested_by": t.contested_by,
                "state": t.state.value,
                "stability": t.stability,
                "region_label": t.region_label,
            }
            for t in list(self._territories.values())[:self._RENDER_MAX_TERRITORIES]
        ]
        snapshot = PoliticalMapSnapshot(
            snapshot_id=f"snap_{self._cycle_count}_{int(time.time() * 1000)}",
            factions=factions_view,
            gradients=gradients_view,
            territories=territories_view,
            rendered_at=time.time(),
            summary=self._render_summary(),
        )
        self._latest_snapshot = snapshot
        self._record_event("phase_render", {
            "snapshot_id": snapshot.snapshot_id,
            "factions_in_snapshot": len(factions_view),
        })
        return {
            "phase": PoliticalCartographyPhase.RENDER.value,
            "snapshot_id": snapshot.snapshot_id,
            "factions_in_snapshot": len(factions_view),
            "gradients_in_snapshot": len(gradients_view),
            "territories_in_snapshot": len(territories_view),
            "summary": snapshot.summary,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _compute_cohesion(self, members: List[str],
                          affinity_edges: Dict[str, Dict[str, float]]) -> float:
        """Compute a 0.0-1.0 cohesion score for a faction's members."""
        if len(members) < 2:
            return 0.0
        total = 0.0
        count = 0
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                score = affinity_edges.get(members[i], {}).get(members[j], 0.0)
                total += max(0.0, score)
                count += 1
        if count == 0:
            return 0.0
        avg = total / count
        return max(0.0, min(1.0, avg))

    def _compute_power(self, members: List[str]) -> float:
        """Compute a 0.0-1.0 raw power score for a faction."""
        if not members:
            return 0.0
        # Power scales with member count and interaction weight, capped at 1.0.
        member_score = min(1.0, len(members) / 6.0)
        interaction_score = 0.0
        for interaction in self._interactions:
            if (interaction.source_agent in members
                    or interaction.target_agent in members):
                interaction_score += interaction.weight * 0.05
        interaction_score = min(1.0, interaction_score)
        return max(0.0, min(1.0, 0.5 * member_score + 0.5 * interaction_score))

    def _classify_cohesion(self, score: float, member_count: int) -> FactionCohesion:
        """Classify a cohesion score into a FactionCohesion label."""
        if member_count < 2:
            return FactionCohesion.FRAGMENTED
        if score >= 0.6:
            return FactionCohesion.TIGHT
        if score >= 0.35:
            return FactionCohesion.COHESIVE
        if score >= 0.15:
            return FactionCohesion.LOOSE
        return FactionCohesion.FRAGMENTED

    def _classify_direction(self, dominant: EmergentFaction,
                            subordinate: EmergentFaction) -> PowerDirection:
        """Classify the direction of a power gradient."""
        # A dominant faction with rising influence is ascending; one whose
        # influence lags its raw power is waning.
        if dominant.influence > 0.6 and dominant.cohesion_score > 0.5:
            return PowerDirection.ASCENDING
        if subordinate.cohesion_score > dominant.cohesion_score:
            return PowerDirection.COLLAPSING
        if dominant.influence < 0.3:
            return PowerDirection.WANING
        return PowerDirection.STABLE

    _FACTION_COLORS = [
        "#d64545", "#4567d6", "#45a8d6", "#67d645", "#d6c445",
        "#a845d6", "#d6458a", "#45d6a8", "#d68a45", "#8a45d6",
        "#45d667", "#d64545",
    ]

    def _pick_color(self, idx: int) -> str:
        return self._FACTION_COLORS[idx % len(self._FACTION_COLORS)]

    def _faction_note(self, members: List[str], cohesion: float) -> str:
        if len(members) < 2:
            holder = members[0] if members else "no one"
            return f"a lone-agent faction holding {holder}"
        if cohesion >= 0.5:
            return f"a tightly bound faction of {len(members)} agents"
        if cohesion >= 0.2:
            return f"a loose alliance of {len(members)} agents"
        return f"a fragmented cluster of {len(members)} agents"

    def _faction_to_dict(self, f: EmergentFaction) -> Dict[str, Any]:
        return {
            "faction_id": f.faction_id,
            "members": list(f.members),
            "cohesion": f.cohesion.value,
            "cohesion_score": f.cohesion_score,
            "power": f.power,
            "influence": f.influence,
            "color": f.color,
            "formed_at_cycle": f.formed_at_cycle,
            "note": f.note,
        }

    def _render_summary(self) -> str:
        factions = len(self._factions)
        contested = sum(
            1 for t in self._territories.values()
            if t.state == TerritoryState.CONTESTED
        )
        vitality = self._derive_vitality().value
        return (
            f"political map: {factions} factions, {contested} contested "
            f"territories, vitality={vitality}"
        )

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "agents": len(self._agents),
                "factions": len(self._factions),
                "gradients": len(self._gradients),
                "territories": len(self._territories),
                "stats": dict(self._stats),
            }

    def get_factions(self) -> List[Dict[str, Any]]:
        with self._global_lock:
            return [
                self._faction_to_dict(f)
                for f in sorted(
                    self._factions.values(),
                    key=lambda f: f.power,
                    reverse=True,
                )
            ]

    def get_faction(self, faction_id: str) -> Dict[str, Any]:
        with self._global_lock:
            faction = self._factions.get(faction_id)
            if faction is None:
                return {"error": f"Faction not found: {faction_id}"}
            return self._faction_to_dict(faction)

    def get_gradients(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._global_lock:
            gradients = sorted(
                self._gradients.values(),
                key=lambda g: g.magnitude,
                reverse=True,
            )[:limit]
            return [
                {
                    "gradient_id": g.gradient_id,
                    "dominant_faction": g.dominant_faction,
                    "subordinate_faction": g.subordinate_faction,
                    "direction": g.direction.value,
                    "magnitude": g.magnitude,
                    "influence_flow": g.influence_flow,
                }
                for g in gradients
            ]

    def get_territories(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._global_lock:
            territories = list(self._territories.values())[:limit]
            return [
                {
                    "territory_id": t.territory_id,
                    "controlling_faction": t.controlling_faction,
                    "contested_by": t.contested_by,
                    "state": t.state.value,
                    "stability": t.stability,
                    "region_label": t.region_label,
                }
                for t in territories
            ]

    def get_map_snapshot(self) -> Dict[str, Any]:
        with self._global_lock:
            if self._latest_snapshot is None:
                return {"error": "No snapshot available yet. Run a cycle first."}
            snap = self._latest_snapshot
            return {
                "snapshot_id": snap.snapshot_id,
                "factions": list(snap.factions),
                "gradients": list(snap.gradients),
                "territories": list(snap.territories),
                "rendered_at": snap.rendered_at,
                "summary": snap.summary,
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic agents and interactions, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_interactions()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_completed": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_interactions(self) -> None:
        """Seed a small synthetic political landscape with agents and interactions."""
        seed_graph = [
            ("sim_alpha", "sim_beta", "cooperative", 0.7),
            ("sim_beta", "sim_alpha", "cooperative", 0.6),
            ("sim_alpha", "sim_gamma", "defense", 0.5),
            ("sim_gamma", "sim_alpha", "defense", 0.5),
            ("sim_beta", "sim_delta", "tribute", 0.4),
            ("sim_delta", "sim_beta", "tribute", 0.4),
            ("sim_epsilon", "sim_zeta", "rivalry", 0.8),
            ("sim_zeta", "sim_epsilon", "rivalry", 0.8),
            ("sim_eta", "sim_theta", "cooperative", 0.6),
            ("sim_theta", "sim_eta", "cooperative", 0.6),
            ("sim_eta", "sim_iota", "cooperative", 0.4),
            ("sim_iota", "sim_eta", "cooperative", 0.4),
            ("sim_alpha", "sim_epsilon", "competitive", 0.5),
            ("sim_epsilon", "sim_alpha", "competitive", 0.5),
        ]
        for src, tgt, kind, weight in seed_graph:
            self.register_interaction(
                src,
                [{"target_agent": tgt, "kind": kind, "weight": weight}],
            )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._interactions.clear()
            self._agents.clear()
            self._factions.clear()
            self._gradients.clear()
            self._territories.clear()
            self._latest_snapshot = None
            self._events_log.clear()
            self._phase = PoliticalCartographyPhase.SURVEY
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
