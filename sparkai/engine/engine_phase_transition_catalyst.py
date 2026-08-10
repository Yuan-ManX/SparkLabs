"""
SparkLabs Engine - Phase Transition Catalyst"""

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

class SystemPhase(Enum):
    """Thermodynamic phases a game system can occupy.

    Ordered from lowest energy (SOLID) to highest energy (PLASMA).
    """
    SOLID = "solid"        # calm, stable, low-intensity
    LIQUID = "liquid"      # flowing, dynamic, moderate-intensity
    GAS = "gas"            # volatile, chaotic, high-intensity
    PLASMA = "plasma"      # transcendent, peak-intensity


class TransitionPhase(Enum):
    """Phases of the catalyst cycle."""
    CHARGE = "charge"
    THRESHOLD = "threshold"
    CATALYZE = "catalyze"
    CASCADE = "cascade"
    DISSIPATE = "dissipate"


class CatalystType(Enum):
    """Types of events that can catalyze phase transitions."""
    BOSS_SPAWN = "boss_spawn"
    PLAYER_DEATH = "player_death"
    MORAL_CHOICE = "moral_choice"
    FACTION_COUP = "faction_coup"
    TIME_OF_DAY = "time_of_day"
    WORLD_EVENT = "world_event"
    QUEST_CLIMAX = "quest_climax"
    DISASTER = "disaster"
    MIRACLE = "miracle"
    BETRAYAL = "betrayal"
    ALLIANCE = "alliance"
    DISCOVERY = "discovery"


class CascadeDirection(Enum):
    """Direction of a cascade transition."""
    UPWARD = "upward"      # energy added, phase may rise
    DOWNWARD = "downward"  # energy removed, phase may fall


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class SystemLink:
    """A directed link between two systems for cascade propagation."""
    source_id: str
    target_id: str
    coupling: float            # 0.0-1.0, how strongly source affects target
    direction: CascadeDirection = CascadeDirection.UPWARD


@dataclass
class GameSystemState:
    """A game system tracked by the catalyst."""
    system_id: str
    label: str
    current_phase: SystemPhase = SystemPhase.SOLID
    energy: float = 0.0           # current energy level (0.0-1.0+)
    base_dissipation: float = 0.02  # energy lost per cycle
    # Hysteresis thresholds per phase transition (energy required to rise)
    rise_thresholds: Dict[SystemPhase, float] = field(default_factory=dict)
    # Energy at which the system falls back to the previous phase
    fall_thresholds: Dict[SystemPhase, float] = field(default_factory=dict)
    # Linked systems for cascade propagation
    links: List[SystemLink] = field(default_factory=list)
    # History of phase transitions
    transition_count: int = 0
    last_transition_time: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CatalystEvent:
    """A catalyst that injects energy into game systems."""
    event_id: str
    catalyst_type: CatalystType
    target_system_ids: List[str]
    energy_delta: float
    timestamp: float
    description: str = ""


@dataclass
class TransitionRecord:
    """Record of a single phase transition."""
    record_id: str
    system_id: str
    system_label: str
    from_phase: SystemPhase
    to_phase: SystemPhase
    direction: CascadeDirection
    trigger_catalyst: Optional[str]
    cascade_depth: int            # 0 = direct catalyst, 1+ = cascaded
    timestamp: float
    energy_before: float
    energy_after: float


@dataclass
class CatalystStats:
    """Aggregate statistics for the catalyst."""
    total_systems: int = 0
    total_catalysts_fired: int = 0
    total_transitions: int = 0
    total_cascades: int = 0
    max_cascade_depth: int = 0
    phase_distribution: Dict[str, int] = field(default_factory=dict)
    avg_energy: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Phase Threshold Defaults
# =============================================================================

# Default hysteresis thresholds for phase transitions.
# rise = energy needed to move UP to the next phase
# fall = energy at which the system drops BACK to the previous phase
DEFAULT_RISE_THRESHOLDS: Dict[SystemPhase, float] = {
    SystemPhase.SOLID: 0.35,    # SOLID -> LIQUID
    SystemPhase.LIQUID: 0.65,   # LIQUID -> GAS
    SystemPhase.GAS: 0.90,      # GAS -> PLASMA
    SystemPhase.PLASMA: 1.5,    # no further phase (saturates)
}

DEFAULT_FALL_THRESHOLDS: Dict[SystemPhase, float] = {
    SystemPhase.SOLID: 0.0,     # cannot fall below SOLID
    SystemPhase.LIQUID: 0.20,   # LIQUID -> SOLID
    SystemPhase.GAS: 0.45,      # GAS -> LIQUID
    SystemPhase.PLASMA: 0.75,   # PLASMA -> GAS
}

# Ordered phase list for neighbor lookup
PHASE_ORDER: List[SystemPhase] = [
    SystemPhase.SOLID,
    SystemPhase.LIQUID,
    SystemPhase.GAS,
    SystemPhase.PLASMA,
]

# Catalyst energy injection table
CATALYST_ENERGY: Dict[CatalystType, float] = {
    CatalystType.BOSS_SPAWN: 0.45,
    CatalystType.PLAYER_DEATH: 0.30,
    CatalystType.MORAL_CHOICE: 0.20,
    CatalystType.FACTION_COUP: 0.55,
    CatalystType.TIME_OF_DAY: 0.10,
    CatalystType.WORLD_EVENT: 0.35,
    CatalystType.QUEST_CLIMAX: 0.40,
    CatalystType.DISASTER: 0.50,
    CatalystType.MIRACLE: 0.35,
    CatalystType.BETRAYAL: 0.30,
    CatalystType.ALLIANCE: 0.15,
    CatalystType.DISCOVERY: 0.20,
}


# =============================================================================
# Engine Phase Transition Catalyst
# =============================================================================

class EnginePhaseTransitionCatalyst:
    """
    Singleton engine module that catalyzes phase transitions in game
    systems based on thermodynamic metaphors.

    The catalyst runs a 5-phase cycle:
      1. CHARGE     - Systems accumulate energy from pending catalysts
      2. THRESHOLD  - Detect systems near or past critical thresholds
      3. CATALYZE   - Trigger phase transitions for systems past thresholds
      4. CASCADE    - Transitions cascade through linked systems
      5. DISSIPATE  - Energy dissipates toward equilibrium
    """

    _instance: Optional["EnginePhaseTransitionCatalyst"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_SYSTEMS = 100
    MAX_TRANSITION_HISTORY = 200
    MAX_CATALYST_HISTORY = 100
    MAX_CASCADE_DEPTH = 4
    MAX_LINKS_PER_SYSTEM = 8
    MIN_ENERGY = 0.0
    MAX_ENERGY = 1.5
    # Cascade propagation factor (energy transferred to linked systems)
    CASCADE_PROPAGATION = 0.5

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._systems: Dict[str, GameSystemState] = {}
        self._pending_catalysts: Deque[CatalystEvent] = deque()
        self._transition_history: Deque[TransitionRecord] = deque(
            maxlen=self.MAX_TRANSITION_HISTORY
        )
        self._catalyst_history: Deque[CatalystEvent] = deque(
            maxlen=self.MAX_CATALYST_HISTORY
        )
        self._stats = CatalystStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "EnginePhaseTransitionCatalyst":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # System Management
    # -------------------------------------------------------------------------

    def register_system(self, system_id: str, label: str,
                        initial_phase: str = "solid",
                        initial_energy: float = 0.0,
                        base_dissipation: float = 0.02,
                        properties: Optional[Dict[str, Any]] = None,
                        ) -> Dict[str, Any]:
        """Register a new game system for phase tracking."""
        with self._lock:
            if system_id in self._systems:
                return {"error": f"System already exists: {system_id}"}
            if len(self._systems) >= self.MAX_SYSTEMS:
                return {"error": "Maximum systems reached"}

            try:
                phase = SystemPhase(initial_phase)
            except ValueError:
                return {"error": f"Unknown phase: {initial_phase}"}

            energy = max(self.MIN_ENERGY, min(self.MAX_ENERGY, float(initial_energy)))
            dissipation = max(0.0, min(0.2, float(base_dissipation)))

            system = GameSystemState(
                system_id=system_id,
                label=label,
                current_phase=phase,
                energy=energy,
                base_dissipation=dissipation,
                rise_thresholds=dict(DEFAULT_RISE_THRESHOLDS),
                fall_thresholds=dict(DEFAULT_FALL_THRESHOLDS),
                properties=properties or {},
            )
            self._systems[system_id] = system
            self._stats.total_systems = len(self._systems)
            self._update_phase_distribution()

            return self._system_to_dict(system)

    def get_system(self, system_id: str) -> Dict[str, Any]:
        """Get the state of a single system."""
        with self._lock:
            sys_state = self._systems.get(system_id)
            if sys_state is None:
                return {"error": f"System not found: {system_id}"}
            return self._system_to_dict(sys_state)

    def list_systems(self) -> Dict[str, Any]:
        """List all tracked systems."""
        with self._lock:
            return {
                "systems": [self._system_to_dict(s) for s in self._systems.values()],
                "total": len(self._systems),
            }

    def remove_system(self, system_id: str) -> Dict[str, Any]:
        """Remove a system from tracking."""
        with self._lock:
            if system_id not in self._systems:
                return {"error": f"System not found: {system_id}"}
            # Also remove links pointing to this system
            for s in self._systems.values():
                s.links = [l for l in s.links if l.target_id != system_id]
            del self._systems[system_id]
            self._stats.total_systems = len(self._systems)
            self._update_phase_distribution()
            return {"removed": system_id}

    def set_thresholds(self, system_id: str,
                       rise_thresholds: Optional[Dict[str, float]] = None,
                       fall_thresholds: Optional[Dict[str, float]] = None,
                       ) -> Dict[str, Any]:
        """Override the hysteresis thresholds for a system."""
        with self._lock:
            sys_state = self._systems.get(system_id)
            if sys_state is None:
                return {"error": f"System not found: {system_id}"}
            if rise_thresholds:
                for phase_str, value in rise_thresholds.items():
                    try:
                        phase = SystemPhase(phase_str)
                        sys_state.rise_thresholds[phase] = float(value)
                    except (ValueError, TypeError):
                        continue
            if fall_thresholds:
                for phase_str, value in fall_thresholds.items():
                    try:
                        phase = SystemPhase(phase_str)
                        sys_state.fall_thresholds[phase] = float(value)
                    except (ValueError, TypeError):
                        continue
            return self._system_to_dict(sys_state)

    # -------------------------------------------------------------------------
    # Link Management
    # -------------------------------------------------------------------------

    def link_systems(self, source_id: str, target_id: str,
                     coupling: float = 0.5,
                     direction: str = "upward") -> Dict[str, Any]:
        """Create a directed link for cascade propagation."""
        with self._lock:
            if source_id not in self._systems:
                return {"error": f"Source system not found: {source_id}"}
            if target_id not in self._systems:
                return {"error": f"Target system not found: {target_id}"}
            if source_id == target_id:
                return {"error": "Cannot link a system to itself"}

            source = self._systems[source_id]
            if len(source.links) >= self.MAX_LINKS_PER_SYSTEM:
                return {"error": "Maximum links reached for source system"}

            # Remove duplicate links
            source.links = [l for l in source.links if l.target_id != target_id]

            try:
                dir_enum = CascadeDirection(direction)
            except ValueError:
                return {"error": f"Unknown direction: {direction}"}

            coupling_val = max(0.0, min(1.0, float(coupling)))
            link = SystemLink(
                source_id=source_id,
                target_id=target_id,
                coupling=coupling_val,
                direction=dir_enum,
            )
            source.links.append(link)
            return {"link": self._link_to_dict(link)}

    def unlink_systems(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Remove a directed link."""
        with self._lock:
            source = self._systems.get(source_id)
            if source is None:
                return {"error": f"Source system not found: {source_id}"}
            before = len(source.links)
            source.links = [l for l in source.links if l.target_id != target_id]
            removed = before - len(source.links)
            return {"removed": removed}

    def list_links(self, system_id: str) -> Dict[str, Any]:
        """List all links from a system."""
        with self._lock:
            sys_state = self._systems.get(system_id)
            if sys_state is None:
                return {"error": f"System not found: {system_id}"}
            return {
                "system_id": system_id,
                "links": [self._link_to_dict(l) for l in sys_state.links],
                "total": len(sys_state.links),
            }

    # -------------------------------------------------------------------------
    # Catalyst Management
    # -------------------------------------------------------------------------

    def fire_catalyst(self, catalyst_type: str,
                      target_system_ids: Optional[List[str]] = None,
                      energy_delta: Optional[float] = None,
                      description: str = "",
                      ) -> Dict[str, Any]:
        """Fire a catalyst that injects energy into target systems.

        If target_system_ids is None, the catalyst affects all systems.
        If energy_delta is None, the default for the catalyst type is used.
        """
        with self._lock:
            try:
                ctype = CatalystType(catalyst_type)
            except ValueError:
                return {"error": f"Unknown catalyst type: {catalyst_type}"}

            if target_system_ids is None:
                targets = list(self._systems.keys())
            else:
                targets = []
                for sid in target_system_ids:
                    if sid in self._systems:
                        targets.append(sid)
                if not targets:
                    return {"error": "No valid target systems"}

            if energy_delta is None:
                energy = CATALYST_ENERGY.get(ctype, 0.2)
            else:
                energy = max(-0.5, min(1.0, float(energy_delta)))

            event = CatalystEvent(
                event_id=f"cat_{int(time.time() * 1000)}_{random.randint(0, 9999)}",
                catalyst_type=ctype,
                target_system_ids=targets,
                energy_delta=energy,
                timestamp=time.time(),
                description=description or f"Catalyst '{ctype.value}' fired",
            )
            self._pending_catalysts.append(event)
            self._catalyst_history.append(event)
            self._stats.total_catalysts_fired += 1

            return {
                "event_id": event.event_id,
                "catalyst_type": ctype.value,
                "targets": targets,
                "energy_delta": energy,
                "description": event.description,
            }

    def list_catalysts(self, limit: int = 20) -> Dict[str, Any]:
        """List recent catalyst events."""
        with self._lock:
            limit = max(1, min(self.MAX_CATALYST_HISTORY, int(limit)))
            items = list(self._catalyst_history)[-limit:]
            items.reverse()
            return {
                "catalysts": [self._catalyst_to_dict(c) for c in items],
                "total": len(self._catalyst_history),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single catalyst cycle.

        Phases: CHARGE -> THRESHOLD -> CATALYZE -> CASCADE -> DISSIPATE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: CHARGE - Apply pending catalysts
            phase = TransitionPhase.CHARGE
            charge_info = self._charge_phase()

            # Phase 2: THRESHOLD - Detect systems near thresholds
            phase = TransitionPhase.THRESHOLD
            threshold_info = self._threshold_phase()

            # Phase 3: CATALYZE - Trigger transitions for past-threshold systems
            phase = TransitionPhase.CATALYZE
            catalyze_info = self._catalyze_phase()

            # Phase 4: CASCADE - Propagate transitions through links
            phase = TransitionPhase.CASCADE
            cascade_info = self._cascade_phase()

            # Phase 5: DISSIPATE - Energy decays back toward equilibrium
            phase = TransitionPhase.DISSIPATE
            dissipate_info = self._dissipate_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()
            self._update_phase_distribution()

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "charge": charge_info,
                "threshold": threshold_info,
                "catalyze": catalyze_info,
                "cascade": cascade_info,
                "dissipate": dissipate_info,
                "total_systems": len(self._systems),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _charge_phase(self) -> Dict[str, Any]:
        """Apply pending catalysts to target systems."""
        applied = 0
        energy_injected = 0.0
        pending_count = len(self._pending_catalysts)

        while self._pending_catalysts:
            event = self._pending_catalysts.popleft()
            for sid in event.target_system_ids:
                sys_state = self._systems.get(sid)
                if sys_state is None:
                    continue
                # Apply energy delta (can be negative)
                before = sys_state.energy
                sys_state.energy = max(
                    self.MIN_ENERGY,
                    min(self.MAX_ENERGY, sys_state.energy + event.energy_delta),
                )
                energy_injected += sys_state.energy - before
                applied += 1

        return {
            "catalysts_processed": pending_count,
            "applications": applied,
            "total_energy_delta": round(energy_injected, 4),
        }

    def _threshold_phase(self) -> Dict[str, Any]:
        """Detect systems near or past critical thresholds."""
        near_rise: List[Dict[str, Any]] = []
        near_fall: List[Dict[str, Any]] = []
        past_rise: List[Dict[str, Any]] = []
        past_fall: List[Dict[str, Any]] = []

        for sys_state in self._systems.values():
            phase_idx = PHASE_ORDER.index(sys_state.current_phase)
            rise_threshold = sys_state.rise_thresholds.get(
                sys_state.current_phase, 1.5
            )
            # For fall threshold we use the current phase's fall value
            fall_threshold = sys_state.fall_thresholds.get(
                sys_state.current_phase, 0.0
            )

            # Check if past rise threshold (and there is a higher phase)
            if phase_idx < len(PHASE_ORDER) - 1:
                if sys_state.energy >= rise_threshold:
                    past_rise.append({
                        "system_id": sys_state.system_id,
                        "label": sys_state.label,
                        "phase": sys_state.current_phase.value,
                        "energy": round(sys_state.energy, 4),
                        "rise_threshold": rise_threshold,
                    })
                elif sys_state.energy >= rise_threshold * 0.85:
                    near_rise.append({
                        "system_id": sys_state.system_id,
                        "label": sys_state.label,
                        "phase": sys_state.current_phase.value,
                        "energy": round(sys_state.energy, 4),
                        "rise_threshold": rise_threshold,
                        "proximity": round(sys_state.energy / rise_threshold, 3),
                    })

            # Check if below fall threshold (and there is a lower phase)
            if phase_idx > 0:
                if sys_state.energy <= fall_threshold:
                    past_fall.append({
                        "system_id": sys_state.system_id,
                        "label": sys_state.label,
                        "phase": sys_state.current_phase.value,
                        "energy": round(sys_state.energy, 4),
                        "fall_threshold": fall_threshold,
                    })
                elif sys_state.energy <= fall_threshold * 1.5 and fall_threshold > 0:
                    near_fall.append({
                        "system_id": sys_state.system_id,
                        "label": sys_state.label,
                        "phase": sys_state.current_phase.value,
                        "energy": round(sys_state.energy, 4),
                        "fall_threshold": fall_threshold,
                    })

        return {
            "near_rise": near_rise,
            "near_fall": near_fall,
            "past_rise": past_rise,
            "past_fall": past_fall,
            "total_near": len(near_rise) + len(near_fall),
            "total_past": len(past_rise) + len(past_fall),
        }

    def _catalyze_phase(self) -> Dict[str, Any]:
        """Trigger transitions for systems past their thresholds."""
        transitions: List[Dict[str, Any]] = []

        for sys_state in self._systems.values():
            phase_idx = PHASE_ORDER.index(sys_state.current_phase)
            rise_threshold = sys_state.rise_thresholds.get(
                sys_state.current_phase, 1.5
            )
            fall_threshold = sys_state.fall_thresholds.get(
                sys_state.current_phase, 0.0
            )

            # Rising transition
            if (phase_idx < len(PHASE_ORDER) - 1
                    and sys_state.energy >= rise_threshold):
                new_phase = PHASE_ORDER[phase_idx + 1]
                record = self._record_transition(
                    sys_state, new_phase, CascadeDirection.UPWARD,
                    trigger=None, cascade_depth=0,
                )
                transitions.append(record)
                continue

            # Falling transition
            if (phase_idx > 0
                    and sys_state.energy <= fall_threshold):
                new_phase = PHASE_ORDER[phase_idx - 1]
                record = self._record_transition(
                    sys_state, new_phase, CascadeDirection.DOWNWARD,
                    trigger=None, cascade_depth=0,
                )
                transitions.append(record)

        return {
            "transitions": transitions,
            "total": len(transitions),
        }

    def _cascade_phase(self) -> Dict[str, Any]:
        """Propagate transitions through linked systems."""
        cascaded: List[Dict[str, Any]] = []
        # Process cascades in breadth-first order up to MAX_CASCADE_DEPTH
        queue: Deque[Tuple[str, CascadeDirection, int, Optional[str]]] = deque()

        # Seed the queue with systems that just transitioned this cycle
        recent_transitions = [
            r for r in list(self._transition_history)
            if r.timestamp >= time.time() - 0.1
        ]
        for rec in recent_transitions:
            queue.append((rec.system_id, rec.direction, 0, rec.system_id))

        visited: Set[str] = set()
        max_depth_reached = 0

        while queue:
            source_id, direction, depth, origin_id = queue.popleft()
            if depth >= self.MAX_CASCADE_DEPTH:
                continue
            if source_id in visited:
                continue
            visited.add(source_id)

            source = self._systems.get(source_id)
            if source is None:
                continue

            for link in source.links:
                if link.direction != direction:
                    continue
                target = self._systems.get(link.target_id)
                if target is None:
                    continue

                # Propagate energy based on coupling
                energy_transfer = 0.0
                if direction == CascadeDirection.UPWARD:
                    energy_transfer = source.energy * link.coupling * self.CASCADE_PROPAGATION
                    target.energy = min(self.MAX_ENERGY, target.energy + energy_transfer)
                else:
                    energy_transfer = source.energy * link.coupling * self.CASCADE_PROPAGATION
                    target.energy = max(self.MIN_ENERGY, target.energy - energy_transfer)

                # Check if target crosses a threshold
                phase_idx = PHASE_ORDER.index(target.current_phase)
                transitioned = False
                if (direction == CascadeDirection.UPWARD
                        and phase_idx < len(PHASE_ORDER) - 1):
                    rise_threshold = target.rise_thresholds.get(
                        target.current_phase, 1.5
                    )
                    if target.energy >= rise_threshold:
                        new_phase = PHASE_ORDER[phase_idx + 1]
                        record = self._record_transition(
                            target, new_phase, CascadeDirection.UPWARD,
                            trigger=origin_id, cascade_depth=depth + 1,
                        )
                        cascaded.append(record)
                        transitioned = True
                        max_depth_reached = max(max_depth_reached, depth + 1)
                elif (direction == CascadeDirection.DOWNWARD
                        and phase_idx > 0):
                    fall_threshold = target.fall_thresholds.get(
                        target.current_phase, 0.0
                    )
                    if target.energy <= fall_threshold:
                        new_phase = PHASE_ORDER[phase_idx - 1]
                        record = self._record_transition(
                            target, new_phase, CascadeDirection.DOWNWARD,
                            trigger=origin_id, cascade_depth=depth + 1,
                        )
                        cascaded.append(record)
                        transitioned = True
                        max_depth_reached = max(max_depth_reached, depth + 1)

                if transitioned:
                    queue.append((target.system_id, direction, depth + 1, origin_id))

        self._stats.total_cascades += len(cascaded)
        self._stats.max_cascade_depth = max(
            self._stats.max_cascade_depth, max_depth_reached
        )

        return {
            "cascaded": cascaded,
            "total": len(cascaded),
            "max_depth": max_depth_reached,
        }

    def _dissipate_phase(self) -> Dict[str, Any]:
        """Energy dissipates toward equilibrium."""
        total_dissipated = 0.0
        systems_decayed = 0

        for sys_state in self._systems.values():
            if sys_state.energy > 0.0:
                decay = sys_state.base_dissipation
                # Higher phases dissipate faster
                phase_idx = PHASE_ORDER.index(sys_state.current_phase)
                phase_multiplier = 1.0 + phase_idx * 0.5
                decay *= phase_multiplier

                before = sys_state.energy
                sys_state.energy = max(
                    self.MIN_ENERGY, sys_state.energy - decay
                )
                total_dissipated += before - sys_state.energy
                if before > sys_state.energy:
                    systems_decayed += 1

        return {
            "total_dissipated": round(total_dissipated, 4),
            "systems_decayed": systems_decayed,
        }

    def _record_transition(self, sys_state: GameSystemState,
                           new_phase: SystemPhase,
                           direction: CascadeDirection,
                           trigger: Optional[str],
                           cascade_depth: int) -> Dict[str, Any]:
        """Record a phase transition."""
        old_phase = sys_state.current_phase
        energy_before = sys_state.energy
        sys_state.current_phase = new_phase
        sys_state.transition_count += 1
        sys_state.last_transition_time = time.time()

        record = TransitionRecord(
            record_id=f"trans_{sys_state.system_id}_{int(time.time() * 1000)}_{random.randint(0, 9999)}",
            system_id=sys_state.system_id,
            system_label=sys_state.label,
            from_phase=old_phase,
            to_phase=new_phase,
            direction=direction,
            trigger_catalyst=trigger,
            cascade_depth=cascade_depth,
            timestamp=time.time(),
            energy_before=round(energy_before, 4),
            energy_after=round(sys_state.energy, 4),
        )
        self._transition_history.append(record)
        self._stats.total_transitions += 1

        return {
            "record_id": record.record_id,
            "system_id": record.system_id,
            "system_label": record.system_label,
            "from_phase": record.from_phase.value,
            "to_phase": record.to_phase.value,
            "direction": record.direction.value,
            "trigger": record.trigger_catalyst,
            "cascade_depth": record.cascade_depth,
            "energy_before": record.energy_before,
            "energy_after": record.energy_after,
        }

    # -------------------------------------------------------------------------
    # Status and History
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get overall status of the catalyst."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "stats": self._stats_to_dict(),
                "pending_catalysts": len(self._pending_catalysts),
            }

    def get_history(self, limit: int = 20) -> Dict[str, Any]:
        """Get recent transition history."""
        with self._lock:
            limit = max(1, min(self.MAX_TRANSITION_HISTORY, int(limit)))
            items = list(self._transition_history)[-limit:]
            items.reverse()
            return {
                "transitions": [
                    {
                        "record_id": r.record_id,
                        "system_id": r.system_id,
                        "system_label": r.system_label,
                        "from_phase": r.from_phase.value,
                        "to_phase": r.to_phase.value,
                        "direction": r.direction.value,
                        "trigger": r.trigger_catalyst,
                        "cascade_depth": r.cascade_depth,
                        "timestamp": r.timestamp,
                        "energy_before": r.energy_before,
                        "energy_after": r.energy_after,
                    }
                    for r in items
                ],
                "total": len(self._transition_history),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles in sequence and seed sample data if empty."""
        with self._lock:
            # Seed sample systems if empty
            if not self._systems:
                templates = [
                    ("sim_combat", "Combat System", "solid", 0.05),
                    ("sim_politics", "Politics System", "solid", 0.05),
                    ("sim_economy", "Economy System", "solid", 0.1),
                    ("sim_narrative", "Narrative System", "solid", 0.08),
                ]
                for sid, label, phase, energy in templates:
                    self.register_system(sid, label, phase, energy)
                # Link systems for cascade propagation
                self.link_systems("sim_politics", "sim_combat", 0.6, "upward")
                self.link_systems("sim_combat", "sim_narrative", 0.4, "upward")
                self.link_systems("sim_economy", "sim_politics", 0.5, "upward")

            # Run cycles with occasional catalysts
            catalyst_choices = list(CatalystType)
            last_cycle_result: Optional[Dict[str, Any]] = None
            for _ in range(cycles):
                if self._systems and random.random() < 0.5:
                    ctype = random.choice(catalyst_choices)
                    self.fire_catalyst(ctype.value)
                last_cycle_result = self.run_cycle()

            return {
                "cycles_run": cycles,
                "last_cycle": last_cycle_result,
                "final_stats": self._stats_to_dict(),
                "status": self.get_status(),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the catalyst to its initial state."""
        with self._lock:
            self._systems.clear()
            self._pending_catalysts.clear()
            self._transition_history.clear()
            self._catalyst_history.clear()
            self._stats = CatalystStats()
            self._cycle_count = 0
            self._active = False
            return {"status": "reset"}

    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------

    def _system_to_dict(self, sys_state: GameSystemState) -> Dict[str, Any]:
        return {
            "system_id": sys_state.system_id,
            "label": sys_state.label,
            "current_phase": sys_state.current_phase.value,
            "energy": round(sys_state.energy, 4),
            "base_dissipation": sys_state.base_dissipation,
            "rise_thresholds": {
                p.value: v for p, v in sys_state.rise_thresholds.items()
            },
            "fall_thresholds": {
                p.value: v for p, v in sys_state.fall_thresholds.items()
            },
            "link_count": len(sys_state.links),
            "transition_count": sys_state.transition_count,
            "last_transition_time": sys_state.last_transition_time,
            "properties": sys_state.properties,
        }

    def _link_to_dict(self, link: SystemLink) -> Dict[str, Any]:
        return {
            "source_id": link.source_id,
            "target_id": link.target_id,
            "coupling": link.coupling,
            "direction": link.direction.value,
        }

    def _catalyst_to_dict(self, c: CatalystEvent) -> Dict[str, Any]:
        return {
            "event_id": c.event_id,
            "catalyst_type": c.catalyst_type.value,
            "target_system_ids": c.target_system_ids,
            "energy_delta": c.energy_delta,
            "timestamp": c.timestamp,
            "description": c.description,
        }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_systems": self._stats.total_systems,
            "total_catalysts_fired": self._stats.total_catalysts_fired,
            "total_transitions": self._stats.total_transitions,
            "total_cascades": self._stats.total_cascades,
            "max_cascade_depth": self._stats.max_cascade_depth,
            "phase_distribution": dict(self._stats.phase_distribution),
            "avg_energy": round(self._stats.avg_energy, 4),
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def _update_phase_distribution(self) -> None:
        dist: Dict[str, int] = {p.value: 0 for p in SystemPhase}
        for sys_state in self._systems.values():
            dist[sys_state.current_phase.value] = (
                dist.get(sys_state.current_phase.value, 0) + 1
            )
        self._stats.phase_distribution = dist

    def _update_avg_metrics(self) -> None:
        if not self._systems:
            self._stats.avg_energy = 0.0
            return
        total = sum(s.energy for s in self._systems.values())
        self._stats.avg_energy = total / len(self._systems)
