"""
SparkLabs Engine - Semantic Gravity Well"""

from __future__ import annotations

import logging
import math
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

class GravityPhase(Enum):
    """Phases of the semantic gravity well cycle."""
    MASS = "mass"           # semantic masses form gravity wells
    ATTRACT = "attract"     # related masses attract
    REPEL = "repel"         # contradictory masses repel
    TIDAL = "tidal"         # tidal forces stretch small masses
    COLLAPSE = "collapse"   # over-dense wells collapse into singularities


class SemanticPolarity(Enum):
    """The polarity of a semantic mass - determines attraction/repulsion."""
    ORDER = "order"             # structure, law, safety
    CHAOS = "chaos"             # disorder, freedom, danger
    LIFE = "life"               # growth, healing, nature
    DEATH = "death"             # decay, ending, necromancy
    LIGHT = "light"             # revelation, truth, hope
    SHADOW = "shadow"           # mystery, secrecy, fear
    MIND = "mind"               # intellect, logic, strategy
    SPIRIT = "spirit"           # faith, emotion, intuition


class MassType(Enum):
    """Types of semantic masses."""
    LOCATION = "location"       # a place with meaning
    CHARACTER = "character"     # a person with meaning
    OBJECT = "object"           # an item with meaning
    EVENT = "event"             # a happening with meaning
    CONCEPT = "concept"         # an abstract idea
    NARRATIVE = "narrative"     # a story thread


class WellState(Enum):
    """State of a gravity well."""
    STABLE = "stable"           # normal gravitational behavior
    GROWING = "growing"         # attracting mass, growing denser
    STRETCHED = "stretched"     # being pulled by tidal forces
    REPULSED = "repulsed"       # being pushed away
    COLLAPSING = "collapsing"   # approaching singularity
    SINGULARITY = "singularity"  # collapsed, all meaning in one point


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SemanticMass:
    """A semantic mass that creates gravitational force."""
    mass_id: str
    label: str
    mass_type: MassType
    polarity: SemanticPolarity
    weight: float = 0.5           # semantic mass (0.0-1.0)
    x: float = 0.5                # position in semantic space (0.0-1.0)
    y: float = 0.5
    vx: float = 0.0               # velocity in semantic space
    vy: float = 0.0
    state: WellState = WellState.STABLE
    attracted_to: Optional[str] = None  # mass_id it's being pulled toward
    repulsed_by: List[str] = field(default_factory=list)
    density: float = 0.5          # how compressed the meaning is
    created_at: float = field(default_factory=time.time)
    last_force_x: float = 0.0
    last_force_y: float = 0.0


@dataclass
class GravityWell:
    """A gravity well formed by a cluster of masses."""
    well_id: str
    center_x: float
    center_y: float
    total_mass: float
    dominant_polarity: SemanticPolarity
    member_masses: Set[str] = field(default_factory=set)
    radius: float = 0.1
    state: WellState = WellState.STABLE
    created_at: float = field(default_factory=time.time)


@dataclass
class TidalStretch:
    """Record of a tidal stretching event."""
    stretch_id: str
    stretched_mass: str
    well_a: str
    well_b: str
    stretch_amount: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class SemanticSingularity:
    """A collapsed well that has become a singularity."""
    singularity_id: str
    source_well: str
    polarity: SemanticPolarity
    total_mass: float
    shed_masses: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Well Engine
# =============================================================================

class EngineSemanticGravityWell:
    """
    Thread-safe singleton orchestrating semantic gravity across the world.

    Usage:
        well = EngineSemanticGravityWell.get_instance()
        well.add_mass("m_tavern", "Tavern", MassType.LOCATION,
                     SemanticPolarity.ORDER, weight=0.6, x=0.3, y=0.5)
        well.add_mass("m_rumor", "Rumor", MassType.NARRATIVE,
                     SemanticPolarity.SHADOW, weight=0.3, x=0.35, y=0.48)
        well.cycle()
    """

    _instance: Optional["EngineSemanticGravityWell"] = None
    _lock = threading.RLock()

    # Polarity attraction/repulsion matrix
    _POLARITY_AFFINITY = {
        (SemanticPolarity.ORDER, SemanticPolarity.ORDER): 1.0,
        (SemanticPolarity.CHAOS, SemanticPolarity.CHAOS): 1.0,
        (SemanticPolarity.LIFE, SemanticPolarity.LIFE): 1.0,
        (SemanticPolarity.DEATH, SemanticPolarity.DEATH): 1.0,
        (SemanticPolarity.LIGHT, SemanticPolarity.LIGHT): 1.0,
        (SemanticPolarity.SHADOW, SemanticPolarity.SHADOW): 1.0,
        (SemanticPolarity.MIND, SemanticPolarity.MIND): 1.0,
        (SemanticPolarity.SPIRIT, SemanticPolarity.SPIRIT): 1.0,
        (SemanticPolarity.ORDER, SemanticPolarity.CHAOS): -1.0,
        (SemanticPolarity.LIFE, SemanticPolarity.DEATH): -1.0,
        (SemanticPolarity.LIGHT, SemanticPolarity.SHADOW): -1.0,
        (SemanticPolarity.MIND, SemanticPolarity.SPIRIT): -0.5,
        (SemanticPolarity.ORDER, SemanticPolarity.LIFE): 0.3,
        (SemanticPolarity.CHAOS, SemanticPolarity.DEATH): 0.3,
        (SemanticPolarity.LIGHT, SemanticPolarity.MIND): 0.3,
        (SemanticPolarity.SHADOW, SemanticPolarity.SPIRIT): 0.3,
    }

    def __init__(self) -> None:
        self._masses: Dict[str, SemanticMass] = {}
        self._wells: Dict[str, GravityWell] = {}
        self._tidal_stretches: Deque[TidalStretch] = deque(maxlen=100)
        self._singularities: Dict[str, SemanticSingularity] = {}
        self._phase: GravityPhase = GravityPhase.MASS
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_masses": 0,
            "total_wells": 0,
            "total_singularities": 0,
            "total_tidal_stretches": 0,
            "attractive_forces": 0,
            "repulsive_forces": 0,
            "avg_mass": 0.0,
            "avg_density": 0.0,
            "singularity_mass": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineSemanticGravityWell":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Mass Management
    # -------------------------------------------------------------------------

    def add_mass(
        self,
        mass_id: str,
        label: str,
        mass_type: MassType,
        polarity: SemanticPolarity,
        weight: float = 0.5,
        x: float = 0.5,
        y: float = 0.5,
    ) -> Dict[str, Any]:
        """Add a semantic mass to the field."""
        with self._global_lock:
            if mass_id in self._masses:
                return {"error": f"Mass already exists: {mass_id}"}
            mass = SemanticMass(
                mass_id=mass_id,
                label=label,
                mass_type=mass_type,
                polarity=polarity,
                weight=max(0.01, min(1.0, weight)),
                x=max(0.0, min(1.0, x)),
                y=max(0.0, min(1.0, y)),
                density=max(0.01, min(1.0, weight)),
            )
            self._masses[mass_id] = mass
            self._stats["total_masses"] = len(self._masses)
            self._record_event("mass_added", {
                "mass_id": mass_id, "polarity": polarity.value,
                "weight": mass.weight,
            })
            return {
                "mass_id": mass_id,
                "label": label,
                "mass_type": mass_type.value,
                "polarity": polarity.value,
                "weight": mass.weight,
                "x": mass.x,
                "y": mass.y,
            }

    def remove_mass(self, mass_id: str) -> Dict[str, Any]:
        """Remove a semantic mass."""
        with self._global_lock:
            if mass_id not in self._masses:
                return {"error": f"Mass not found: {mass_id}"}
            m = self._masses.pop(mass_id)
            # remove from wells
            for well in self._wells.values():
                well.member_masses.discard(mass_id)
            self._stats["total_masses"] = len(self._masses)
            return {"removed": mass_id, "label": m.label}

    # -------------------------------------------------------------------------
    # Phase: MASS - form gravity wells from clusters
    # -------------------------------------------------------------------------

    def _phase_mass(self) -> Dict[str, Any]:
        """Form gravity wells from clusters of nearby masses."""
        # clear old wells
        self._wells.clear()
        # cluster masses by proximity and polarity
        assigned: Set[str] = set()
        well_count = 0
        for mid, m in self._masses.items():
            if mid in assigned:
                continue
            if m.state == WellState.SINGULARITY:
                continue
            # start a new well
            members = {mid}
            assigned.add(mid)
            for oid, om in self._masses.items():
                if oid in assigned:
                    continue
                if om.state == WellState.SINGULARITY:
                    continue
                # check proximity
                dist = math.sqrt((m.x - om.x) ** 2 + (m.y - om.y) ** 2)
                if dist < 0.2:
                    # check polarity affinity
                    affinity = self._get_affinity(m.polarity, om.polarity)
                    if affinity >= 0:
                        members.add(oid)
                        assigned.add(oid)
            if len(members) >= 1:
                well_id = f"well_{well_count}"
                well_count += 1
                # compute center
                member_list = list(members)
                xs = [self._masses[mid].x for mid in member_list]
                ys = [self._masses[mid].y for mid in member_list]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                total_mass = sum(self._masses[mid].weight for mid in member_list)
                # dominant polarity
                polarity_counts: Dict[SemanticPolarity, float] = {}
                for mid in member_list:
                    p = self._masses[mid].polarity
                    polarity_counts[p] = polarity_counts.get(p, 0.0) + self._masses[mid].weight
                dominant = max(polarity_counts, key=polarity_counts.get) if polarity_counts else SemanticPolarity.ORDER
                well = GravityWell(
                    well_id=well_id,
                    center_x=cx,
                    center_y=cy,
                    total_mass=total_mass,
                    dominant_polarity=dominant,
                    member_masses=members,
                    radius=min(0.3, 0.05 + total_mass * 0.02),
                )
                self._wells[well_id] = well
        self._stats["total_wells"] = len(self._wells)
        return {"wells_formed": len(self._wells)}

    # -------------------------------------------------------------------------
    # Phase: ATTRACT - related masses pull toward each other
    # -------------------------------------------------------------------------

    def _phase_attract(self) -> Dict[str, Any]:
        """Related masses attract each other."""
        attractive = 0
        mass_list = list(self._masses.values())
        for i in range(len(mass_list)):
            ma = mass_list[i]
            if ma.state == WellState.SINGULARITY:
                continue
            for j in range(i + 1, len(mass_list)):
                mb = mass_list[j]
                if mb.state == WellState.SINGULARITY:
                    continue
                affinity = self._get_affinity(ma.polarity, mb.polarity)
                if affinity <= 0:
                    continue
                # compute distance
                dx = mb.x - ma.x
                dy = mb.y - ma.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 0.01:
                    continue
                # gravitational force
                force = affinity * ma.weight * mb.weight / (dist * dist + 0.01)
                force = min(0.05, force)  # cap force
                # apply force
                fx = force * dx / dist
                fy = force * dy / dist
                ma.vx += fx / max(0.01, ma.weight)
                ma.vy += fy / max(0.01, ma.weight)
                mb.vx -= fx / max(0.01, mb.weight)
                mb.vy -= fy / max(0.01, mb.weight)
                ma.last_force_x = fx
                ma.last_force_y = fy
                mb.last_force_x = -fx
                mb.last_force_y = -fy
                if affinity > 0.5:
                    ma.attracted_to = mb.mass_id
                    mb.attracted_to = ma.mass_id
                    ma.state = WellState.GROWING
                    mb.state = WellState.GROWING
                attractive += 1
        self._stats["attractive_forces"] = attractive
        return {"attractive_pairs": attractive}

    # -------------------------------------------------------------------------
    # Phase: REPEL - contradictory masses push apart
    # -------------------------------------------------------------------------

    def _phase_repel(self) -> Dict[str, Any]:
        """Contradictory masses repel each other."""
        repulsive = 0
        mass_list = list(self._masses.values())
        for i in range(len(mass_list)):
            ma = mass_list[i]
            if ma.state == WellState.SINGULARITY:
                continue
            for j in range(i + 1, len(mass_list)):
                mb = mass_list[j]
                if mb.state == WellState.SINGULARITY:
                    continue
                affinity = self._get_affinity(ma.polarity, mb.polarity)
                if affinity >= 0:
                    continue
                # compute distance
                dx = mb.x - ma.x
                dy = mb.y - ma.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 0.01:
                    dist = 0.01
                # repulsive force (inverse of gravity)
                force = abs(affinity) * ma.weight * mb.weight / (dist * dist + 0.01)
                force = min(0.08, force)
                # apply repulsive force (push apart)
                fx = force * dx / dist
                fy = force * dy / dist
                ma.vx -= fx / max(0.01, ma.weight)
                ma.vy -= fy / max(0.01, ma.weight)
                mb.vx += fx / max(0.01, mb.weight)
                mb.vy += fy / max(0.01, mb.weight)
                if ma.mass_id not in mb.repulsed_by:
                    mb.repulsed_by.append(ma.mass_id)
                if mb.mass_id not in ma.repulsed_by:
                    ma.repulsed_by.append(mb.mass_id)
                ma.state = WellState.REPULSED
                mb.state = WellState.REPULSED
                repulsive += 1
        self._stats["repulsive_forces"] = repulsive
        return {"repulsive_pairs": repulsive}

    # -------------------------------------------------------------------------
    # Phase: TIDAL - tidal forces stretch small masses
    # -------------------------------------------------------------------------

    def _phase_tidal(self) -> Dict[str, Any]:
        """Large wells stretch small masses between them."""
        stretches = 0
        # find the two largest wells
        sorted_wells = sorted(self._wells.values(), key=lambda w: w.total_mass, reverse=True)
        if len(sorted_wells) < 2:
            # apply velocity and update positions
            self._apply_velocities()
            return {"tidal_stretches": 0}
        well_a = sorted_wells[0]
        well_b = sorted_wells[1]
        # check if they have different polarities (tidal force is strongest between opposites)
        affinity = self._get_affinity(well_a.dominant_polarity, well_b.dominant_polarity)
        if affinity >= 0:
            self._apply_velocities()
            return {"tidal_stretches": 0}
        # find small masses between the two wells
        for m in self._masses.values():
            if m.state == WellState.SINGULARITY:
                continue
            if m.weight > 0.4:
                continue  # only small masses are stretched
            # check if mass is between the two wells
            dist_a = math.sqrt((m.x - well_a.center_x) ** 2 + (m.y - well_a.center_y) ** 2)
            dist_b = math.sqrt((m.x - well_b.center_x) ** 2 + (m.y - well_b.center_y) ** 2)
            total_dist = math.sqrt((well_a.center_x - well_b.center_x) ** 2 + (well_a.center_y - well_b.center_y) ** 2)
            if dist_a + dist_b > total_dist * 1.2:
                continue  # not between them
            # tidal stretch
            stretch_amount = abs(affinity) * well_a.total_mass * well_b.total_mass * 0.01
            m.density = max(0.1, m.density - stretch_amount * 0.5)
            m.state = WellState.STRETCHED
            stretch_id = f"stretch_{self._cycle_count}_{stretches}"
            self._tidal_stretches.append(TidalStretch(
                stretch_id=stretch_id,
                stretched_mass=m.mass_id,
                well_a=well_a.well_id,
                well_b=well_b.well_id,
                stretch_amount=stretch_amount,
            ))
            stretches += 1
            self._record_event("tidal_stretch", {
                "mass_id": m.mass_id, "well_a": well_a.well_id,
                "well_b": well_b.well_id,
            })
        self._stats["total_tidal_stretches"] = len(self._tidal_stretches)
        self._apply_velocities()
        return {"tidal_stretches": stretches}

    def _apply_velocities(self) -> None:
        """Apply velocities to positions and dampen."""
        for m in self._masses.values():
            if m.state == WellState.SINGULARITY:
                continue
            m.x = max(0.0, min(1.0, m.x + m.vx))
            m.y = max(0.0, min(1.0, m.y + m.vy))
            # dampen velocity
            m.vx *= 0.7
            m.vy *= 0.7
            # density increases as mass clusters
            if m.state == WellState.GROWING:
                m.density = min(1.0, m.density + 0.02)
            elif m.state == WellState.STRETCHED:
                pass  # density already reduced
            else:
                m.density = max(0.1, m.density - 0.005)

    # -------------------------------------------------------------------------
    # Phase: COLLAPSE - over-dense wells collapse into singularities
    # -------------------------------------------------------------------------

    def _phase_collapse(self) -> Dict[str, Any]:
        """Over-dense wells collapse into singularities."""
        collapsed = 0
        shed = 0
        for well in list(self._wells.values()):
            if well.total_mass > 2.0 and well.state != WellState.SINGULARITY:
                # collapse into singularity
                singularity_id = f"sing_{well.well_id}"
                # find the heaviest mass to be the singularity core
                member_masses = [self._masses[mid] for mid in well.member_masses if mid in self._masses]
                if not member_masses:
                    continue
                core = max(member_masses, key=lambda m: m.weight)
                core.state = WellState.SINGULARITY
                core.density = 1.0
                # shed excess masses
                shed_masses = []
                for m in member_masses:
                    if m is core:
                        continue
                    # lighter masses are shed
                    if m.weight < core.weight * 0.5:
                        shed_masses.append(m.mass_id)
                        m.state = WellState.STABLE
                        m.density = max(0.1, m.density * 0.5)
                        # give them a velocity away from the singularity
                        dx = m.x - core.x
                        dy = m.y - core.y
                        dist = math.sqrt(dx * dx + dy * dy) + 0.01
                        m.vx += dx / dist * 0.05
                        m.vy += dy / dist * 0.05
                        shed += 1
                singularity = SemanticSingularity(
                    singularity_id=singularity_id,
                    source_well=well.well_id,
                    polarity=well.dominant_polarity,
                    total_mass=well.total_mass,
                    shed_masses=shed_masses,
                )
                self._singularities[singularity_id] = singularity
                well.state = WellState.SINGULARITY
                collapsed += 1
                self._record_event("well_collapsed", {
                    "singularity_id": singularity_id,
                    "source_well": well.well_id,
                    "shed_count": len(shed_masses),
                })
        self._stats["total_singularities"] = len(self._singularities)
        self._stats["singularity_mass"] = sum(s.total_mass for s in self._singularities.values())
        return {"wells_collapsed": collapsed, "masses_shed": shed}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single semantic gravity well cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = GravityPhase.MASS
            phase_outputs["mass"] = self._phase_mass()
            self._phase = GravityPhase.ATTRACT
            phase_outputs["attract"] = self._phase_attract()
            self._phase = GravityPhase.REPEL
            phase_outputs["repel"] = self._phase_repel()
            self._phase = GravityPhase.TIDAL
            phase_outputs["tidal"] = self._phase_tidal()
            self._phase = GravityPhase.COLLAPSE
            phase_outputs["collapse"] = self._phase_collapse()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles in sequence."""
        if cycles < 1:
            cycles = 1
        if cycles > 100:
            cycles = 100
        for _ in range(cycles):
            self.cycle()
        return {"cycles_run": cycles, "stats": dict(self._stats)}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_mass(self, mass_id: str) -> Dict[str, Any]:
        """Get a mass's state."""
        with self._global_lock:
            m = self._masses.get(mass_id)
            if m is None:
                return {"error": f"Mass not found: {mass_id}"}
            return {
                "mass_id": m.mass_id,
                "label": m.label,
                "mass_type": m.mass_type.value,
                "polarity": m.polarity.value,
                "weight": m.weight,
                "x": m.x,
                "y": m.y,
                "vx": m.vx,
                "vy": m.vy,
                "state": m.state.value,
                "density": m.density,
                "attracted_to": m.attracted_to,
                "repulsed_by": m.repulsed_by,
            }

    def get_all_masses(self) -> List[Dict[str, Any]]:
        """Get all masses."""
        with self._global_lock:
            return [
                {
                    "mass_id": m.mass_id,
                    "label": m.label,
                    "polarity": m.polarity.value,
                    "weight": m.weight,
                    "x": m.x,
                    "y": m.y,
                    "state": m.state.value,
                    "density": m.density,
                }
                for m in self._masses.values()
            ]

    def get_wells(self) -> List[Dict[str, Any]]:
        """Get all gravity wells."""
        with self._global_lock:
            return [
                {
                    "well_id": w.well_id,
                    "center_x": w.center_x,
                    "center_y": w.center_y,
                    "total_mass": w.total_mass,
                    "dominant_polarity": w.dominant_polarity.value,
                    "member_count": len(w.member_masses),
                    "radius": w.radius,
                    "state": w.state.value,
                }
                for w in self._wells.values()
            ]

    def get_singularities(self) -> List[Dict[str, Any]]:
        """Get all singularities."""
        with self._global_lock:
            return [
                {
                    "singularity_id": s.singularity_id,
                    "source_well": s.source_well,
                    "polarity": s.polarity.value,
                    "total_mass": s.total_mass,
                    "shed_count": len(s.shed_masses),
                }
                for s in self._singularities.values()
            ]

    def get_tidal_stretches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent tidal stretches."""
        with self._global_lock:
            recent = list(self._tidal_stretches)[-limit:]
            return [
                {
                    "stretch_id": t.stretch_id,
                    "stretched_mass": t.stretched_mass,
                    "well_a": t.well_a,
                    "well_b": t.well_b,
                    "stretch_amount": t.stretch_amount,
                }
                for t in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get well status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire well."""
        with self._global_lock:
            count = len(self._masses)
            self._masses.clear()
            self._wells.clear()
            self._tidal_stretches.clear()
            self._singularities.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = GravityPhase.MASS
            self._stats = {
                "total_masses": 0,
                "total_wells": 0,
                "total_singularities": 0,
                "total_tidal_stretches": 0,
                "attractive_forces": 0,
                "repulsive_forces": 0,
                "avg_mass": 0.0,
                "avg_density": 0.0,
                "singularity_mass": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "masses_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _get_affinity(self, a: SemanticPolarity, b: SemanticPolarity) -> float:
        """Get the affinity between two polarities (-1 to 1)."""
        if a == b:
            return 1.0
        key = (a, b)
        if key in self._POLARITY_AFFINITY:
            return self._POLARITY_AFFINITY[key]
        rev_key = (b, a)
        if rev_key in self._POLARITY_AFFINITY:
            return self._POLARITY_AFFINITY[rev_key]
        return 0.0  # neutral by default

    def _update_stats(self) -> None:
        if self._masses:
            self._stats["avg_mass"] = sum(m.weight for m in self._masses.values()) / len(self._masses)
            self._stats["avg_density"] = sum(m.density for m in self._masses.values()) / len(self._masses)
        self._stats["total_masses"] = len(self._masses)
        self._stats["total_wells"] = len(self._wells)
        self._stats["total_singularities"] = len(self._singularities)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
