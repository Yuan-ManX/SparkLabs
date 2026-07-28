"""
SparkLabs Agent - Mythogenic Flux Conductor

The AgentMythogenicFluxConductor models how myths and legends flux
through an agent population, conducting narrative energy from one
carrier to the next. Rather than treating story as a fixed text, the
conductor treats myth as a living current that flows between agents,
gaining or losing charge as it encounters believers, skeptics, and
re-tellers.

Myths are not stored - they are conducted. A legend lives only in the
act of being told, and each telling mutates it. The conductor models
this: a myth starts as a seed in one agent, flows along conductance
channels to others, and at each hop it is re-shaped by the carrier's
temperament. A myth that passes through a poet grows more vivid. One
that passes through a skeptic grows more abstract. One that passes
through a child grows more wondrous.

The conductor also models mythic corruption (festering). When a myth
cannot flow - when its carriers hoard it or its channels are blocked -
it festers, becoming a dogma, a taboo, or a curse. Festered myths
exert a different kind of power: they constrain rather than inspire.
The conductor's health depends on keeping mythic flux circulating,
letting old myths die gracefully so new ones can be born.

Architecture:
  MYTHOGEN  ->  CONDUCT   ->  FLUX     ->  LEGEND    ->  FESTER
  (myth      (myth flows   (flux builds (legend      (blocked myths
   seeds     along         charge and   crystallizes fester into
   crystall- conductance   shapes the   when flux    dogma/curse,
   ize in    channels      carrier's    peaks)       draining the
   agents)   between       temperament)              conductor)
   agents)   agents)

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
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ConductorPhase(Enum):
    """Phases of the mythogenic flux cycle."""
    MYTHOGEN = "mythogen"     # myth seeds crystallize in agents
    CONDUCT = "conduct"       # myth flows along conductance channels
    FLUX = "flux"             # flux builds and shapes the carrier
    LEGEND = "legend"         # legends crystallize at flux peaks
    FESTER = "fester"         # blocked myths fester into dogma/curse


class MythType(Enum):
    """Categories of myths that flow through the conductor."""
    ORIGIN = "origin"             # how things began
    EPIC = "epic"                 # heroic deeds
    TRAGEDY = "tragedy"           # noble failure
    PROPHECY = "prophecy"         # what will come
    FOLK = "folk"                 # everyday wisdom
    TABOO = "taboo"               # what must not be done
    CURSE = "curse"               # lingering ill will
    BLESSING = "blessing"         # lingering good will


class MythState(Enum):
    """Lifecycle state of a flowing myth."""
    SEED = "seed"                 # just crystallized, not yet flowing
    FLOWING = "flowing"           # actively being conducted
    CHARGED = "charged"           # flux has built up
    LEGENDARY = "legendary"       # crystallized into a legend
    FESTERING = "festering"       # blocked, beginning to fester
    CORRUPTED = "corrupted"       # fully festering myth
    FADED = "faded"               # lost all charge, dissolved


class CarrierTemperament(Enum):
    """Temperaments that shape how an agent conducts myth."""
    POET = "poet"                 # makes myths more vivid
    SKEPTIC = "skeptic"           # makes myths more abstract
    CHILD = "child"               # makes myths more wondrous
    ELDER = "elder"               # makes myths more solemn
    TRICKSTER = "trickster"       # makes myths more ironic
    MYSTIC = "mystic"             # makes myths more transcendent
    HISTORIAN = "historian"       # makes myths more grounded


class ConductanceType(Enum):
    """How two agents conduct myth between them."""
    ORAL = "oral"                 # spoken tradition
    RITUAL = "ritual"             # ceremonial reenactment
    ARTIFACT = "artifact"         # physical object carries myth
    DREAM = "dream"               # shared dream
    OMEN = "omen"                 # observed sign
    INHERITANCE = "inheritance"   # passed down through generations


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MythSeed:
    """A myth crystallizing in an agent."""
    myth_id: str
    origin_agent: str
    myth_type: MythType
    title: str
    content: str
    charge: float = 0.5          # narrative energy (0.0-1.0)
    state: MythState = MythState.SEED
    current_carrier: str = ""    # agent currently holding the myth
    carrier_history: List[str] = field(default_factory=list)
    temperament_trail: List[CarrierTemperament] = field(default_factory=list)
    tellings: int = 0
    flux_accumulated: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_flow: float = field(default_factory=time.time)
    festering_cycles: int = 0
    legend_strength: float = 0.0


@dataclass
class ConductanceChannel:
    """A channel through which myth flows between two agents."""
    channel_id: str
    agent_a: str
    agent_b: str
    conductance_type: ConductanceType
    bandwidth: float = 0.5       # how much myth can flow (0.0-1.0)
    clarity: float = 0.7         # how intact myth survives (0.0-1.0)
    last_used: float = field(default_factory=time.time)
    total_myths_conducted: int = 0


@dataclass
class CarrierAgent:
    """Per-agent conductor state."""
    agent_id: str
    temperament: CarrierTemperament
    carried_myths: Set[str] = field(default_factory=set)  # myth_ids
    channels: Dict[str, str] = field(default_factory=dict)  # channel_id -> partner_id
    mythogenic_pressure: float = 0.0  # pressure to generate new myths
    total_seeded: int = 0
    total_conducted: int = 0
    total_legends: int = 0
    total_festered: int = 0
    receptivity: float = 0.5     # how open to new myths


@dataclass
class Legend:
    """A crystallized legend born from mythic flux."""
    legend_id: str
    source_myth: str
    title: str
    power: float                 # cultural power (0.0-1.0)
    spread: int                  # how many agents know it
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Conductor
# =============================================================================

class AgentMythogenicFluxConductor:
    """
    Thread-safe singleton orchestrating mythogenic flux across agents.

    Usage:
        conductor = AgentMythogenicFluxConductor.get_instance()
        conductor.register_agent("bard", CarrierTemperament.POET)
        conductor.register_agent("scribe", CarrierTemperament.HISTORIAN)
        conductor.open_channel("ch_1", "bard", "scribe", ConductanceType.ORAL)
        conductor.seed_myth("m_1", "bard", MythType.EPIC, "The Fall", "A city sank")
        conductor.cycle()
    """

    _instance: Optional["AgentMythogenicFluxConductor"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._agents: Dict[str, CarrierAgent] = {}
        self._myths: Dict[str, MythSeed] = {}
        self._channels: Dict[str, ConductanceChannel] = {}
        self._legends: Dict[str, Legend] = {}
        self._phase: ConductorPhase = ConductorPhase.MYTHOGEN
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_myths": 0,
            "total_channels": 0,
            "total_legends": 0,
            "flowing_myths": 0,
            "festering_myths": 0,
            "corrupted_myths": 0,
            "faded_myths": 0,
            "total_tellings": 0,
            "avg_charge": 0.0,
            "avg_flux": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentMythogenicFluxConductor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        temperament: CarrierTemperament,
        receptivity: float = 0.5,
    ) -> Dict[str, Any]:
        """Register a new carrier agent."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents[agent_id] = CarrierAgent(
                agent_id=agent_id,
                temperament=temperament,
                receptivity=max(0.0, min(1.0, receptivity)),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {
                "agent_id": agent_id, "temperament": temperament.value,
            })
            return {
                "agent_id": agent_id,
                "temperament": temperament.value,
                "receptivity": self._agents[agent_id].receptivity,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and release their myths."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            # release carried myths
            for myth_id in a.carried_myths:
                m = self._myths.get(myth_id)
                if m and m.current_carrier == agent_id:
                    m.state = MythState.FADED
            # remove channels
            for cid in list(a.channels.keys()):
                self._channels.pop(cid, None)
                partner = a.channels.get(cid)
                if partner and partner in self._agents:
                    self._agents[partner].channels.pop(cid, None)
            self._stats["total_agents"] = len(self._agents)
            self._stats["total_channels"] = len(self._channels)
            return {"removed": agent_id, "myths_released": len(a.carried_myths)}

    # -------------------------------------------------------------------------
    # Channel Management
    # -------------------------------------------------------------------------

    def open_channel(
        self,
        channel_id: str,
        agent_a: str,
        agent_b: str,
        conductance_type: ConductanceType,
        bandwidth: float = 0.5,
        clarity: float = 0.7,
    ) -> Dict[str, Any]:
        """Open a conductance channel between two agents."""
        with self._global_lock:
            if agent_a not in self._agents or agent_b not in self._agents:
                return {"error": "Agent not found"}
            if agent_a == agent_b:
                return {"error": "Cannot channel to self"}
            if channel_id in self._channels:
                return {"error": f"Channel already exists: {channel_id}"}
            channel = ConductanceChannel(
                channel_id=channel_id,
                agent_a=agent_a,
                agent_b=agent_b,
                conductance_type=conductance_type,
                bandwidth=max(0.0, min(1.0, bandwidth)),
                clarity=max(0.0, min(1.0, clarity)),
            )
            self._channels[channel_id] = channel
            self._agents[agent_a].channels[channel_id] = agent_b
            self._agents[agent_b].channels[channel_id] = agent_a
            self._stats["total_channels"] = len(self._channels)
            self._record_event("channel_opened", {
                "channel_id": channel_id, "a": agent_a, "b": agent_b,
                "type": conductance_type.value,
            })
            return {
                "channel_id": channel_id,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "conductance_type": conductance_type.value,
                "bandwidth": channel.bandwidth,
                "clarity": channel.clarity,
            }

    # -------------------------------------------------------------------------
    # Myth Seeding
    # -------------------------------------------------------------------------

    def seed_myth(
        self,
        myth_id: str,
        origin_agent: str,
        myth_type: MythType,
        title: str,
        content: str,
        initial_charge: float = 0.5,
    ) -> Dict[str, Any]:
        """Seed a new myth in an agent."""
        with self._global_lock:
            if origin_agent not in self._agents:
                return {"error": f"Agent not found: {origin_agent}"}
            if myth_id in self._myths:
                return {"error": f"Myth already exists: {myth_id}"}
            myth = MythSeed(
                myth_id=myth_id,
                origin_agent=origin_agent,
                myth_type=myth_type,
                title=title,
                content=content,
                charge=max(0.1, min(1.0, initial_charge)),
                current_carrier=origin_agent,
                carrier_history=[origin_agent],
            )
            self._myths[myth_id] = myth
            self._agents[origin_agent].carried_myths.add(myth_id)
            self._agents[origin_agent].total_seeded += 1
            self._stats["total_myths"] = len(self._myths)
            self._record_event("myth_seeded", {
                "myth_id": myth_id, "origin": origin_agent,
                "type": myth_type.value, "title": title,
            })
            return {
                "myth_id": myth_id,
                "origin_agent": origin_agent,
                "myth_type": myth_type.value,
                "title": title,
                "charge": myth.charge,
            }

    # -------------------------------------------------------------------------
    # Phase: MYTHOGEN - spontaneous myth generation
    # -------------------------------------------------------------------------

    def _phase_mythogen(self) -> Dict[str, Any]:
        """Agents under mythogenic pressure spontaneously generate myths."""
        seeded = 0
        for a in self._agents.values():
            if a.mythogenic_pressure < 0.6:
                continue
            if random.random() > 0.3:
                continue
            myth_id = f"m_spont_{self._cycle_count}_{seeded}"
            mtype = random.choice(list(MythType))
            title = f"Spontaneous {mtype.value}"
            content = f"A myth born of pressure in {a.agent_id}"
            result = self.seed_myth(myth_id, a.agent_id, mtype, title, content, 0.4)
            if "error" not in result:
                seeded += 1
                a.mythogenic_pressure = max(0.0, a.mythogenic_pressure - 0.4)
        return {"spontaneous_seeded": seeded}

    # -------------------------------------------------------------------------
    # Phase: CONDUCT - myths flow along channels
    # -------------------------------------------------------------------------

    def _phase_conduct(self) -> Dict[str, Any]:
        """Myths flow from carriers to connected agents."""
        conducted = 0
        for myth in self._myths.values():
            if myth.state in (MythState.FADED, MythState.CORRUPTED, MythState.LEGENDARY):
                continue
            carrier = self._agents.get(myth.current_carrier)
            if carrier is None:
                continue
            # try to conduct to a connected agent
            if not carrier.channels:
                # no channels - myth festers
                myth.festering_cycles += 1
                continue
            # pick a random channel
            channel_id = random.choice(list(carrier.channels.keys()))
            channel = self._channels.get(channel_id)
            if channel is None:
                continue
            partner_id = carrier.channels[channel_id]
            partner = self._agents.get(partner_id)
            if partner is None:
                continue
            # check if partner will receive (based on receptivity and bandwidth)
            if random.random() > partner.receptivity * channel.bandwidth:
                # rejected - myth festers slightly
                myth.festering_cycles += 1
                continue
            # conduct the myth
            myth.current_carrier = partner_id
            myth.carrier_history.append(partner_id)
            myth.temperament_trail.append(partner.temperament)
            myth.tellings += 1
            myth.last_flow = time.time()
            myth.festering_cycles = 0
            if myth.state == MythState.SEED:
                myth.state = MythState.FLOWING
            elif myth.state == MythState.FESTERING:
                myth.state = MythState.FLOWING
            # update carrier stats
            carrier.total_conducted += 1
            partner.carried_myths.add(myth.myth_id)
            carrier.carried_myths.discard(myth.myth_id)
            channel.last_used = time.time()
            channel.total_myths_conducted += 1
            conducted += 1
            self._record_event("myth_conducted", {
                "myth_id": myth.myth_id, "from": carrier.agent_id,
                "to": partner_id, "channel": channel_id,
            })
        self._stats["total_tellings"] = sum(m.tellings for m in self._myths.values())
        return {"myths_conducted": conducted}

    # -------------------------------------------------------------------------
    # Phase: FLUX - charge builds and shapes the carrier's temperament
    # -------------------------------------------------------------------------

    def _phase_flux(self) -> Dict[str, Any]:
        """Flux builds as myths pass through agents, shaped by temperament."""
        charged = 0
        for myth in self._myths.values():
            if myth.state in (MythState.FADED, MythState.CORRUPTED, MythState.LEGENDARY):
                continue
            # charge builds with each telling
            charge_gain = 0.05 + 0.02 * myth.tellings
            # temperament shapes the myth
            carrier = self._agents.get(myth.current_carrier)
            if carrier is None:
                continue
            temp_effect = {
                CarrierTemperament.POET: 0.08,      # vivid - more charge
                CarrierTemperament.SKEPTIC: -0.03,   # abstract - less charge
                CarrierTemperament.CHILD: 0.06,      # wondrous - more charge
                CarrierTemperament.ELDER: 0.02,      # solemn - slight gain
                CarrierTemperament.TRICKSTER: 0.04,  # ironic - moderate gain
                CarrierTemperament.MYSTIC: 0.10,     # transcendent - most charge
                CarrierTemperament.HISTORIAN: -0.01, # grounded - slight drain
            }
            charge_gain += temp_effect.get(carrier.temperament, 0.0)
            myth.charge = max(0.0, min(1.0, myth.charge + charge_gain))
            myth.flux_accumulated += myth.charge * 0.1
            # build pressure on carrier
            carrier.mythogenic_pressure = min(1.0, carrier.mythogenic_pressure + 0.05)
            if myth.charge > 0.7 and myth.state == MythState.FLOWING:
                myth.state = MythState.CHARGED
                charged += 1
        return {"myths_charged": charged}

    # -------------------------------------------------------------------------
    # Phase: LEGEND - charged myths crystallize into legends
    # -------------------------------------------------------------------------

    def _phase_legend(self) -> Dict[str, Any]:
        """Charged myths with high flux crystallize into legends."""
        crystallized = 0
        for myth in list(self._myths.values()):
            if myth.state != MythState.CHARGED:
                continue
            if myth.flux_accumulated < 1.0 or myth.tellings < 3:
                continue
            # crystallize into a legend
            legend_id = f"leg_{myth.myth_id}"
            if legend_id not in self._legends:
                legend = Legend(
                    legend_id=legend_id,
                    source_myth=myth.myth_id,
                    title=myth.title,
                    power=myth.charge * min(1.0, myth.tellings / 10.0),
                    spread=len(set(myth.carrier_history)),
                )
                self._legends[legend_id] = legend
                myth.state = MythState.LEGENDARY
                myth.legend_strength = legend.power
                crystallized += 1
                # credit the carrier
                carrier = self._agents.get(myth.current_carrier)
                if carrier:
                    carrier.total_legends += 1
                self._record_event("legend_crystallized", {
                    "legend_id": legend_id, "source_myth": myth.myth_id,
                    "power": legend.power, "spread": legend.spread,
                })
        self._stats["total_legends"] = len(self._legends)
        return {"legends_crystallized": crystallized}

    # -------------------------------------------------------------------------
    # Phase: FESTER - blocked myths corrupt into dogma/curse
    # -------------------------------------------------------------------------

    def _phase_fester(self) -> Dict[str, Any]:
        """Myths that cannot flow fester and corrupt."""
        festering = 0
        corrupted = 0
        faded = 0
        for myth in self._myths.values():
            if myth.state in (MythState.LEGENDARY, MythState.FADED, MythState.CORRUPTED):
                continue
            # check if myth is festering (festering_cycles set by conduct phase)
            if myth.festering_cycles > 0:
                myth.charge = max(0.0, myth.charge - 0.01)
                if myth.state not in (MythState.FESTERING,):
                    myth.state = MythState.FESTERING
                festering += 1
                # after 8 festering cycles, corrupt
                if myth.festering_cycles > 8:
                    myth.state = MythState.CORRUPTED
                    # corrupted myths transform type
                    if myth.myth_type not in (MythType.CURSE, MythType.TABOO):
                        myth.myth_type = random.choice([MythType.CURSE, MythType.TABOO])
                    corrupted += 1
                    carrier = self._agents.get(myth.current_carrier)
                    if carrier:
                        carrier.total_festered += 1
                    self._record_event("myth_corrupted", {
                        "myth_id": myth.myth_id,
                        "new_type": myth.myth_type.value,
                    })
            # myths with no charge fade
            if myth.charge < 0.05 and myth.state != MythState.FADED:
                myth.state = MythState.FADED
                faded += 1
                carrier = self._agents.get(myth.current_carrier)
                if carrier:
                    carrier.carried_myths.discard(myth.myth_id)
        return {
            "festering": festering,
            "corrupted": corrupted,
            "faded": faded,
        }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single mythogenic flux cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ConductorPhase.MYTHOGEN
            phase_outputs["mythogen"] = self._phase_mythogen()
            self._phase = ConductorPhase.CONDUCT
            phase_outputs["conduct"] = self._phase_conduct()
            self._phase = ConductorPhase.FLUX
            phase_outputs["flux"] = self._phase_flux()
            self._phase = ConductorPhase.LEGEND
            phase_outputs["legend"] = self._phase_legend()
            self._phase = ConductorPhase.FESTER
            phase_outputs["fester"] = self._phase_fester()
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

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get an agent's conductor state."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "temperament": a.temperament.value,
                "receptivity": a.receptivity,
                "carried_myths": len(a.carried_myths),
                "channels": len(a.channels),
                "mythogenic_pressure": a.mythogenic_pressure,
                "total_seeded": a.total_seeded,
                "total_conducted": a.total_conducted,
                "total_legends": a.total_legends,
                "total_festered": a.total_festered,
            }

    def get_myth(self, myth_id: str) -> Dict[str, Any]:
        """Get a myth's state."""
        with self._global_lock:
            m = self._myths.get(myth_id)
            if m is None:
                return {"error": f"Myth not found: {myth_id}"}
            return {
                "myth_id": m.myth_id,
                "origin_agent": m.origin_agent,
                "myth_type": m.myth_type.value,
                "title": m.title,
                "content": m.content,
                "charge": m.charge,
                "state": m.state.value,
                "current_carrier": m.current_carrier,
                "carrier_history": m.carrier_history,
                "temperament_trail": [t.value for t in m.temperament_trail],
                "tellings": m.tellings,
                "flux_accumulated": m.flux_accumulated,
                "festering_cycles": m.festering_cycles,
                "legend_strength": m.legend_strength,
            }

    def get_all_myths(self) -> List[Dict[str, Any]]:
        """Get all myths."""
        with self._global_lock:
            return [
                {
                    "myth_id": m.myth_id,
                    "title": m.title,
                    "type": m.myth_type.value,
                    "state": m.state.value,
                    "charge": m.charge,
                    "tellings": m.tellings,
                    "current_carrier": m.current_carrier,
                }
                for m in self._myths.values()
            ]

    def get_legends(self) -> List[Dict[str, Any]]:
        """Get all crystallized legends."""
        with self._global_lock:
            return [
                {
                    "legend_id": l.legend_id,
                    "source_myth": l.source_myth,
                    "title": l.title,
                    "power": l.power,
                    "spread": l.spread,
                    "created_at": l.created_at,
                }
                for l in self._legends.values()
            ]

    def get_channels(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get channels, optionally filtered by agent."""
        with self._global_lock:
            result = []
            for c in self._channels.values():
                if agent_id and agent_id not in (c.agent_a, c.agent_b):
                    continue
                result.append({
                    "channel_id": c.channel_id,
                    "agent_a": c.agent_a,
                    "agent_b": c.agent_b,
                    "conductance_type": c.conductance_type.value,
                    "bandwidth": c.bandwidth,
                    "clarity": c.clarity,
                    "total_myths_conducted": c.total_myths_conducted,
                })
            return result

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get conductor status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire conductor."""
        with self._global_lock:
            count = len(self._agents)
            self._agents.clear()
            self._myths.clear()
            self._channels.clear()
            self._legends.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = ConductorPhase.MYTHOGEN
            self._stats = {
                "total_agents": 0,
                "total_myths": 0,
                "total_channels": 0,
                "total_legends": 0,
                "flowing_myths": 0,
                "festering_myths": 0,
                "corrupted_myths": 0,
                "faded_myths": 0,
                "total_tellings": 0,
                "avg_charge": 0.0,
                "avg_flux": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "agents_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        if self._myths:
            self._stats["avg_charge"] = sum(m.charge for m in self._myths.values()) / len(self._myths)
            self._stats["avg_flux"] = sum(m.flux_accumulated for m in self._myths.values()) / len(self._myths)
            self._stats["flowing_myths"] = sum(1 for m in self._myths.values() if m.state in (MythState.FLOWING, MythState.CHARGED))
            self._stats["festering_myths"] = sum(1 for m in self._myths.values() if m.state == MythState.FESTERING)
            self._stats["corrupted_myths"] = sum(1 for m in self._myths.values() if m.state == MythState.CORRUPTED)
            self._stats["faded_myths"] = sum(1 for m in self._myths.values() if m.state == MythState.FADED)
        self._stats["total_myths"] = len(self._myths)
        self._stats["total_legends"] = len(self._legends)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
