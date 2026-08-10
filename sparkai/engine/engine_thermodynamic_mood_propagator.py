"""
SparkLabs Engine - Thermodynamic Mood Propagator"""

from __future__ import annotations

import logging
import random
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

class PropagationPhase(Enum):
    """Phases of the mood propagation cycle."""
    SAMPLE = "sample"            # read the current mood field
    DIFFUSE = "diffuse"          # flow mood heat across the adjacency graph
    EQUILIBRATE = "equilibrate"  # pull each cell toward local thermal balance
    DISSIPATE = "dissipate"      # vent excess entropy, check conservation
    COMMIT = "commit"            # lock in the new field and write events


class ThermalPhase(Enum):
    """Per-cell thermal phase, derived from temperature thresholds."""
    COLD = "cold"                # low thermal intensity
    WARM = "warm"                # moderate thermal intensity
    HOT = "hot"                  # high thermal intensity
    INCANDESCENT = "incandescent"  # near-saturation thermal intensity
    SUPERCOOLED = "supercooled"  # near-zero thermal intensity


class MoodLabel(Enum):
    """The felt quality of a cell's thermal state."""
    CALM = "calm"
    TENSE = "tense"
    EUPHORIC = "euphoric"
    MELANCHOLY = "melancholy"
    AGITATED = "agitated"
    SERENE = "serene"


class EntropyVent(Enum):
    """How wide a cell's entropy vent is open."""
    CLOSED = "closed"            # no venting
    PARTIAL = "partial"          # trickle venting
    OPEN = "open"                # steady venting
    MAXIMAL = "maximal"          # full bleed


class Vitality(Enum):
    """How alive a cell's mood field is, derived from temperature."""
    LATENT = "latent"            # barely any thermal activity
    EMERGING = "emerging"        # beginning to warm
    ACTIVE = "active"            # steady thermal activity
    SURGING = "surging"          # strong thermal activity
    SATURATED = "saturated"      # thermal activity maxed out


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MoodCell:
    """A single mood cell in the spatial thermal field."""
    cell_id: str
    entity_id: str                       # the region_key, e.g. "region_north"
    region_name: str
    temperature_k: float = 0.5           # 0.0-1.0 normalized thermal intensity
    entropy_bits: float = 0.3            # 0.0-1.0 dispersed energy
    thermal_phase: ThermalPhase = ThermalPhase.WARM
    mood_label: MoodLabel = MoodLabel.CALM
    vent_state: EntropyVent = EntropyVent.CLOSED
    vitality: Vitality = Vitality.ACTIVE
    conductivity: float = 0.42           # how readily heat flows in/out
    neighbors: List[str] = field(default_factory=list)
    last_sampled_at: float = field(default_factory=time.time)
    last_committed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PropagationConfig:
    """Tuning knobs for the thermodynamic mood propagator."""
    max_cells: int = 200
    conductivity_default: float = 0.42
    diffusion_rate: float = 0.18
    equilibration_tolerance: float = 0.05
    entropy_vent_threshold: float = 0.75
    supercool_threshold: float = 0.10
    incandescent_threshold: float = 0.90


# =============================================================================
# Propagator
# =============================================================================

class ThermodynamicMoodPropagator:
    """
    Thread-safe singleton orchestrating thermodynamic mood propagation.

    Usage:
        prop = ThermodynamicMoodPropagator.get_instance()
        prop.register_cell(entity_id="region_north", region_name="North Quadrant")
        prop.cycle()
        state = prop.get_cell(cell_id)
    """

    _instance: Optional["ThermodynamicMoodPropagator"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Cell cap (mirrors PropagationConfig.max_cells default).
    _MAX_CELLS = 200
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._cells: Dict[str, MoodCell] = {}
        self._phase: PropagationPhase = PropagationPhase.SAMPLE
        self._cycle_count: int = 0
        self._cell_counter: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._config: PropagationConfig = PropagationConfig()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ThermodynamicMoodPropagator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> Dict[str, Any]:
        self._stats = {
            "cycles_completed": 0,
            "uptime_started_at": time.time(),
            "cells_registered": 0,
            "phase_runs": 0,
            "diffusion_steps": 0,
            "equilibration_passes": 0,
            "entropy_dissipated": 0.0,
            "thermal_transitions": 0,
            "vents_opened": 0,
            "events_recorded": 0,
        }
        return self._stats

    def _update_stats(self, **kwargs: Any) -> None:
        # Increment numeric stats that already exist; ignore unknown keys so
        # callers cannot smuggle in new counters.
        for key, value in kwargs.items():
            if key not in self._stats:
                continue
            current = self._stats[key]
            if isinstance(current, (int, float)) and isinstance(value, (int, float)):
                self._stats[key] = current + value
            else:
                self._stats[key] = value

    def _record_event(self, event_type: str,
                      payload: Optional[Dict[str, Any]] = None) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload or {},
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })
        self._update_stats(events_recorded=1)

    # -------------------------------------------------------------------------
    # Cell Management
    # -------------------------------------------------------------------------

    def register_cell(self, entity_id: str, region_name: str,
                      temperature_k: float = 0.5,
                      entropy_bits: float = 0.3,
                      mood_label: Optional[MoodLabel] = None,
                      conductivity: Optional[float] = None,
                      neighbors: Optional[List[str]] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Register a new mood cell keyed by its entity_id (region_key)."""
        with self._global_lock:
            if entity_id in self._cells:
                return {"error": f"mood cell already registered for entity: {entity_id}"}
            if len(self._cells) >= self._MAX_CELLS:
                return {"error": f"max cells cap reached ({self._MAX_CELLS})"}

            self._cell_counter += 1
            cell_id = f"mcell_{self._cell_counter:04d}"
            temp = max(0.0, min(1.0, float(temperature_k)))
            entropy = max(0.0, min(1.0, float(entropy_bits)))
            cond = (self._config.conductivity_default
                    if conductivity is None
                    else max(0.0, min(1.0, float(conductivity))))
            label = mood_label if mood_label is not None else self._derive_mood_label_from(temp, entropy)

            cell = MoodCell(
                cell_id=cell_id,
                entity_id=entity_id,
                region_name=region_name,
                temperature_k=temp,
                entropy_bits=entropy,
                thermal_phase=self._derive_thermal_phase_from(temp),
                mood_label=label,
                vent_state=EntropyVent.CLOSED,
                vitality=self._derive_vitality_from(temp),
                conductivity=cond,
                neighbors=list(neighbors) if neighbors else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._cells[entity_id] = cell
            self._update_stats(cells_registered=1)
            self._record_event("cell_registered", {
                "cell_id": cell_id,
                "entity_id": entity_id,
                "region_name": region_name,
            })
            return self._serialize_cell(cell)

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single propagation cycle through all five phases."""
        with self._global_lock:
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count

            # Seed a small synthetic field on the first cycle if none exists.
            if not self._cells:
                self._seed_synthetic_cells()

            phase_outputs: List[Dict[str, Any]] = []
            self._phase = PropagationPhase.SAMPLE
            phase_outputs.append(self._phase_sample())
            self._phase = PropagationPhase.DIFFUSE
            phase_outputs.append(self._phase_diffuse())
            self._phase = PropagationPhase.EQUILIBRATE
            phase_outputs.append(self._phase_equilibrate())
            self._phase = PropagationPhase.DISSIPATE
            phase_outputs.append(self._phase_dissipate())
            self._phase = PropagationPhase.COMMIT
            phase_outputs.append(self._phase_commit())

            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_sample(self) -> Dict[str, Any]:
        """SAMPLE: read the current mood field (temperatures, entropies, adjacency)."""
        sampled = 0
        adjacency: Dict[str, List[str]] = {}
        now = time.time()
        for entity_id, cell in self._cells.items():
            cell.last_sampled_at = now
            adjacency[entity_id] = list(cell.neighbors)
            sampled += 1
        self._update_stats(phase_runs=1)
        self._record_event("phase_sample", {"sampled": sampled})
        return {
            "phase": "sample",
            "sampled": sampled,
            "adjacency_size": len(adjacency),
        }

    def _phase_diffuse(self) -> Dict[str, Any]:
        """DIFFUSE: flow mood heat across the adjacency graph using conductivity."""
        steps = 0
        deltas: Dict[str, float] = {}
        for entity_id, cell in self._cells.items():
            neighbor_cells = [self._cells[n]
                              for n in cell.neighbors if n in self._cells]
            if not neighbor_cells:
                continue
            avg_temp = sum(c.temperature_k for c in neighbor_cells) / len(neighbor_cells)
            # Heat flows toward equilibrium scaled by conductivity and the
            # global diffusion rate (a stand-in for thermal conductivity).
            flow = (self._config.diffusion_rate * cell.conductivity
                    * (avg_temp - cell.temperature_k))
            deltas[entity_id] = flow
            steps += 1
        for entity_id, flow in deltas.items():
            cell = self._cells[entity_id]
            cell.temperature_k = max(0.0, min(1.0, cell.temperature_k + flow))
            # Diffusion stirs entropy slightly as energy moves.
            cell.entropy_bits = max(0.0, min(1.0, cell.entropy_bits + abs(flow) * 0.05))
        self._update_stats(phase_runs=1, diffusion_steps=steps)
        self._record_event("phase_diffuse", {"diffusion_steps": steps})
        return {"phase": "diffuse", "diffusion_steps": steps}

    def _phase_equilibrate(self) -> Dict[str, Any]:
        """EQUILIBRATE: pull cells toward local thermal balance; re-derive mood labels."""
        passes = 0
        for entity_id, cell in self._cells.items():
            neighbor_cells = [self._cells[n]
                              for n in cell.neighbors if n in self._cells]
            if neighbor_cells:
                avg_temp = sum(c.temperature_k for c in neighbor_cells) / len(neighbor_cells)
                if abs(avg_temp - cell.temperature_k) > self._config.equilibration_tolerance:
                    # Move halfway toward the local average to approach balance.
                    cell.temperature_k = (cell.temperature_k + avg_temp) * 0.5
                    passes += 1
            # Re-derive the felt mood label from the (possibly shifted) thermal state.
            cell.mood_label = self._derive_mood_label_from(cell.temperature_k, cell.entropy_bits)
            passes += 1
        self._update_stats(phase_runs=1, equilibration_passes=passes)
        self._record_event("phase_equilibrate", {"equilibration_passes": passes})
        return {"phase": "equilibrate", "equilibration_passes": passes}

    def _phase_dissipate(self) -> Dict[str, Any]:
        """DISSIPATE: vent excess entropy; enforce conservation of the energy budget."""
        dissipated = 0.0
        vents_opened = 0
        for entity_id, cell in self._cells.items():
            if cell.entropy_bits > self._config.entropy_vent_threshold:
                cell.vent_state = self._scale_vent(cell.entropy_bits)
                vents_opened += 1
                # Venting bleeds entropy off; the dissipated energy leaves the field.
                spill = cell.entropy_bits * 0.3
                cell.entropy_bits = max(0.0, cell.entropy_bits - spill)
                dissipated += spill
            elif cell.vent_state != EntropyVent.CLOSED:
                # Below threshold, ease the vent back toward closed.
                cell.vent_state = EntropyVent.PARTIAL
            # Conservation checks: temperature and entropy stay in [0, 1].
            cell.entropy_bits = max(0.0, min(1.0, cell.entropy_bits))
            cell.temperature_k = max(0.0, min(1.0, cell.temperature_k))
        self._update_stats(phase_runs=1,
                           entropy_dissipated=dissipated,
                           vents_opened=vents_opened)
        self._record_event("phase_dissipate", {
            "entropy_dissipated": dissipated,
            "vents_opened": vents_opened,
        })
        return {
            "phase": "dissipate",
            "entropy_dissipated": dissipated,
            "vents_opened": vents_opened,
        }

    def _phase_commit(self) -> Dict[str, Any]:
        """COMMIT: lock in the new field state, update thermal phase, write events."""
        committed = 0
        transitions = 0
        now = time.time()
        for entity_id, cell in self._cells.items():
            prev_phase = cell.thermal_phase
            cell.thermal_phase = self._derive_thermal_phase_from(cell.temperature_k)
            if cell.thermal_phase != prev_phase:
                transitions += 1
            cell.vitality = self._derive_vitality_from(cell.temperature_k)
            cell.last_committed_at = now
            committed += 1
        self._update_stats(phase_runs=1, thermal_transitions=transitions)
        self._record_event("phase_commit", {
            "committed": committed,
            "thermal_transitions": transitions,
        })
        return {
            "phase": "commit",
            "committed": committed,
            "thermal_transitions": transitions,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _derive_thermal_phase_from(self, temperature_k: float) -> ThermalPhase:
        t = max(0.0, min(1.0, temperature_k))
        if t >= self._config.incandescent_threshold:
            return ThermalPhase.INCANDESCENT
        if t <= self._config.supercool_threshold:
            return ThermalPhase.SUPERCOOLED
        if t < 0.33:
            return ThermalPhase.COLD
        if t < 0.66:
            return ThermalPhase.WARM
        return ThermalPhase.HOT

    def _derive_mood_label_from(self, temperature_k: float,
                                entropy_bits: float) -> MoodLabel:
        t = max(0.0, min(1.0, temperature_k))
        e = max(0.0, min(1.0, entropy_bits))
        if e >= 0.7:
            return MoodLabel.AGITATED
        if t >= 0.7:
            return MoodLabel.EUPHORIC
        if t <= 0.2 and e <= 0.2:
            return MoodLabel.SERENE
        if t <= 0.3:
            return MoodLabel.MELANCHOLY
        if e >= 0.5:
            return MoodLabel.TENSE
        return MoodLabel.CALM

    def _derive_vitality_from(self, temperature_k: float) -> Vitality:
        t = max(0.0, min(1.0, temperature_k))
        if t >= 0.9:
            return Vitality.SATURATED
        if t >= 0.66:
            return Vitality.SURGING
        if t >= 0.33:
            return Vitality.ACTIVE
        if t >= 0.1:
            return Vitality.EMERGING
        return Vitality.LATENT

    def _scale_vent(self, entropy_bits: float) -> EntropyVent:
        e = max(0.0, min(1.0, entropy_bits))
        if e >= 0.95:
            return EntropyVent.MAXIMAL
        if e >= 0.85:
            return EntropyVent.OPEN
        return EntropyVent.PARTIAL

    def _serialize_cell(self, cell: MoodCell) -> Dict[str, Any]:
        return {
            "cell_id": cell.cell_id,
            "entity_id": cell.entity_id,
            "region_name": cell.region_name,
            "temperature_k": cell.temperature_k,
            "entropy_bits": cell.entropy_bits,
            "thermal_phase": cell.thermal_phase.value,
            "mood_label": cell.mood_label.value,
            "vent_state": cell.vent_state.value,
            "vitality": cell.vitality.value,
            "conductivity": cell.conductivity,
            "neighbors": list(cell.neighbors),
            "last_sampled_at": cell.last_sampled_at,
            "last_committed_at": cell.last_committed_at,
            "metadata": dict(cell.metadata),
        }

    def _seed_synthetic_cells(self) -> None:
        """Seed a small synthetic mood field (6 cells) with a hub-and-ring adjacency."""
        # Hub at the center, ring of regions around it, plus one leaf.
        seeds = [
            ("region_center", "Central Hub", 0.62, 0.45, MoodLabel.EUPHORIC),
            ("region_north", "North Quadrant", 0.55, 0.30, MoodLabel.CALM),
            ("region_south", "South Reach", 0.72, 0.55, MoodLabel.TENSE),
            ("region_east", "Eastern March", 0.40, 0.20, MoodLabel.SERENE),
            ("region_west", "Western Vale", 0.85, 0.80, MoodLabel.AGITATED),
            ("region_edge", "Edge Lands", 0.15, 0.10, MoodLabel.MELANCHOLY),
        ]
        adjacency = {
            "region_center": ["region_north", "region_south", "region_east", "region_west"],
            "region_north": ["region_center", "region_east", "region_edge"],
            "region_south": ["region_center", "region_west"],
            "region_east": ["region_center", "region_north"],
            "region_west": ["region_center", "region_south"],
            "region_edge": ["region_north"],
        }
        for entity_id, region_name, temp, entropy, label in seeds:
            if entity_id in self._cells:
                continue
            # Small jitter keeps the synthetic field from being perfectly uniform.
            jitter_t = max(0.0, min(1.0, temp + random.uniform(-0.03, 0.03)))
            self.register_cell(
                entity_id=entity_id,
                region_name=region_name,
                temperature_k=jitter_t,
                entropy_bits=entropy,
                mood_label=label,
                neighbors=adjacency.get(entity_id, []),
            )

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "cells": len(self._cells),
                "stats": dict(self._stats),
            }

    def get_cells(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            cells = sorted(
                self._cells.values(),
                key=lambda c: c.last_committed_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(cells),
                "cells": [self._serialize_cell(c) for c in cells],
            }

    def get_cell(self, cell_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id (the region_key), NOT by
        # cell_id, so we search the values for a matching cell_id.
        with self._global_lock:
            for cell in self._cells.values():
                if cell.cell_id == cell_id:
                    return self._serialize_cell(cell)
            return {"error": "mood cell not found", "cell_id": cell_id}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple propagation cycles back-to-back."""
        with self._global_lock:
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._cells.clear()
            self._events_log.clear()
            self._phase = PropagationPhase.SAMPLE
            self._cycle_count = 0
            self._cell_counter = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
