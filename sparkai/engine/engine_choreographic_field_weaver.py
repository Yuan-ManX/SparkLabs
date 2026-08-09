"""
SparkLabs Engine - Choreographic Field Weaver"""

from __future__ import annotations

import logging
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

class ChoreographicPhase(Enum):
    """Phases of the choreographic field cycle."""
    NOTATE = "notate"        # notate movement lines for each staged entity
    STAGE = "stage"          # stage entities onto the field at starting positions
    COUPLE = "couple"        # couple lines whose motions should respond to one another
    FLOW = "flow"            # flow the whole field forward through the choreography
    RESOLVE = "resolve"      # resolve the pattern: settle entities that reached line end


class MovementQuality(Enum):
    """The qualitative texture of a single entity's motion through the field."""
    FLOWING = "flowing"        # continuous, smooth traversal of waypoints
    STACCATO = "staccato"      # clipped, punctuated motion between waypoints
    SUSPENDED = "suspended"    # held, slow motion with delay at each waypoint
    PERCUSSIVE = "percussive"  # sharp bursts of motion, abrupt stops
    VIBRATORY = "vibratory"    # rapid small oscillations along the line


class CoupleRelation(Enum):
    """How two coupled lines relate to one another through the field."""
    LEAD_FOLLOW = "lead_follow"    # one line drives, the other tracks with delay
    MIRROR = "mirror"              # lines reflect each other across the field axis
    COUNTERPOINT = "counterpoint"  # lines move in independent but responsive voices
    UNISON = "unison"              # lines move together at the same pace and phase


class LineState(Enum):
    """State of an individual movement line as it passes through the cycle."""
    NOTATED = "notated"      # waypoints have been notated, entity not yet staged
    STAGED = "staged"        # entity placed at starting position on the field
    COUPLED = "coupled"      # line has been linked to one or more partner lines
    FLOWING = "flowing"      # entity is advancing along its waypoints
    SETTLED = "settled"      # entity reached its final waypoint and settled


class FieldCoherence(Enum):
    """How coordinated the field is as a whole."""
    DISPERSED = "dispersed"      # lines are independent, no shared motion
    COORDINATING = "coordinating"  # coupling is forming, motion beginning to align
    COHERENT = "coherent"        # lines move as a coordinated body
    HARMONIZED = "harmonized"    # lines are fully synchronized and resolved


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MovementLine:
    """A notated trajectory for a single entity through the field."""
    line_id: str
    entity_id: str
    quality: MovementQuality
    waypoints: List[List[float]] = field(default_factory=list)  # each [x, y] in 0.0-1.0
    current_step: float = 0.0          # progress along waypoints, 0.0 to len(waypoints)-1
    state: LineState = LineState.NOTATED
    created_at: float = field(default_factory=time.time)

    def position(self) -> Tuple[float, float]:
        """Interpolate the entity's current [x, y] position along its waypoints."""
        if not self.waypoints:
            return (0.0, 0.0)
        if len(self.waypoints) == 1:
            return (self.waypoints[0][0], self.waypoints[0][1])
        idx_f = max(0.0, min(float(len(self.waypoints) - 1), self.current_step))
        i = int(idx_f)
        frac = idx_f - i
        if i >= len(self.waypoints) - 1:
            wp = self.waypoints[-1]
            return (wp[0], wp[1])
        a = self.waypoints[i]
        b = self.waypoints[i + 1]
        return (a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac)


@dataclass
class CoupleBond:
    """A coupling between two movement lines whose motions should respond."""
    bond_id: str
    line_a_id: str
    line_b_id: str
    relation: CoupleRelation
    strength: float = 0.5              # 0.0-1.0, how strongly the bond pulls partners
    created_at: float = field(default_factory=time.time)


@dataclass
class ChoreographicField:
    """Per-field state holding lines, bonds, positions, and coherence."""
    field_id: str
    lines: Dict[str, MovementLine] = field(default_factory=dict)
    bonds: Dict[str, CoupleBond] = field(default_factory=dict)
    field_position: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    coherence: FieldCoherence = FieldCoherence.DISPERSED
    total_notated: int = 0
    total_staged: int = 0
    total_coupled: int = 0
    total_flowed: int = 0
    total_settled: int = 0
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Weaver
# =============================================================================

class EngineChoreographicFieldWeaver:
    """
    Thread-safe singleton orchestrating choreographic field weaving.

    Usage:
        weaver = EngineChoreographicFieldWeaver.get_instance()
        weaver.register_field("stage_a")
        weaver.add_entity("stage_a", "dancer_1", MovementQuality.FLOWING)
        weaver.cycle()
        state = weaver.get_field_state("stage_a")
    """

    _instance: Optional["EngineChoreographicFieldWeaver"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _NOTATE_WAYPOINTS = 4                 # default waypoint count for a notated line
    _STAGE_DEFAULT_SPACING = 0.2          # spacing between staged entities on the field
    _COUPLE_MAX_BONDS = 6                 # cap on bonds synthesized per field
    _FLOW_STEP_SIZE = 0.15                # progress advanced per flow step
    _RESOLVE_COMPLETION_THRESHOLD = 0.95  # progress past which a line is settled
    _MAX_LINES_PER_FIELD = 20
    _MAX_FIELDS = 30
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._fields: Dict[str, ChoreographicField] = {}
        self._phase: ChoreographicPhase = ChoreographicPhase.NOTATE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineChoreographicFieldWeaver":
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
            "total_fields": 0,
            "total_lines": 0,
            "total_bonds": 0,
            "total_notated": 0,
            "total_staged": 0,
            "total_coupled": 0,
            "total_flowed": 0,
            "total_settled": 0,
            "open_lines": 0,
            "avg_progress": 0.0,
            "coherence": FieldCoherence.DISPERSED.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._fields:
            return
        progresses: List[float] = []
        open_lines = 0
        for f in self._fields.values():
            for line in f.lines.values():
                if line.state != LineState.SETTLED:
                    open_lines += 1
                progresses.append(self._line_progress(line))
            f.coherence = self._compute_coherence(f)
        self._stats["total_fields"] = len(self._fields)
        self._stats["total_lines"] = sum(len(f.lines) for f in self._fields.values())
        self._stats["total_bonds"] = sum(len(f.bonds) for f in self._fields.values())
        self._stats["open_lines"] = open_lines
        self._stats["avg_progress"] = (
            sum(progresses) / len(progresses) if progresses else 0.0
        )
        # Derive overall coherence from the most coherent field's band.
        self._stats["coherence"] = self._derive_coherence_band().value

    def _derive_coherence_band(self) -> FieldCoherence:
        """Aggregate field-level coherence values into one overall band."""
        if not self._fields:
            return FieldCoherence.DISPERSED
        bands = [f.coherence for f in self._fields.values()]
        # Weight toward the most coherent field so a single harmonized field
        # lifts the whole system out of the dispersed band.
        most_coherent = max(bands, key=lambda c: list(FieldCoherence).index(c))
        return most_coherent

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Field Management
    # -------------------------------------------------------------------------

    def register_field(self, field_id: str) -> Dict[str, Any]:
        """Register a new choreographic field for weaving."""
        with self._global_lock:
            if field_id in self._fields:
                return {"error": f"Field already registered: {field_id}"}
            if len(self._fields) >= self._MAX_FIELDS:
                return {"error": f"Field capacity reached ({self._MAX_FIELDS})"}
            f = ChoreographicField(field_id=field_id)
            self._fields[field_id] = f
            self._record_event("field_registered", {"field_id": field_id})
            return {
                "field_id": field_id,
                "coherence": f.coherence.value,
            }

    def remove_field(self, field_id: str) -> Dict[str, Any]:
        with self._global_lock:
            f = self._fields.pop(field_id, None)
            if f is None:
                return {"error": f"Field not found: {field_id}"}
            self._record_event("field_removed", {"field_id": field_id})
            return {
                "removed": field_id,
                "cleared_lines": len(f.lines),
                "cleared_bonds": len(f.bonds),
            }

    def add_entity(self, field_id: str, entity_id: str,
                   quality: MovementQuality) -> Dict[str, Any]:
        """Register an entity on a field with a movement quality.

        The movement line is notated during the next NOTATE phase.
        """
        with self._global_lock:
            f = self._fields.get(field_id)
            if f is None:
                return {"error": f"Field not found: {field_id}"}
            line_id = f"line_{entity_id}_{field_id}"
            if line_id in f.lines:
                return {"error": f"Entity already on field: {entity_id}"}
            if len(f.lines) >= self._MAX_LINES_PER_FIELD:
                return {"error": f"Line capacity reached for field: {field_id}"}
            line = MovementLine(
                line_id=line_id,
                entity_id=entity_id,
                quality=quality,
                waypoints=[],
                state=LineState.NOTATED,
            )
            f.lines[line_id] = line
            self._record_event("entity_added", {
                "field_id": field_id,
                "entity_id": entity_id,
                "line_id": line_id,
                "quality": quality.value,
            })
            return {
                "field_id": field_id,
                "entity_id": entity_id,
                "line_id": line_id,
                "quality": quality.value,
            }

    def couple(self, field_id: str, bond_id: str, line_a_id: str,
               line_b_id: str, relation: CoupleRelation,
               strength: float = 0.5) -> Dict[str, Any]:
        """Create a couple bond between two movement lines on a field."""
        with self._global_lock:
            f = self._fields.get(field_id)
            if f is None:
                return {"error": f"Field not found: {field_id}"}
            if line_a_id not in f.lines:
                return {"error": f"Line not found: {line_a_id}"}
            if line_b_id not in f.lines:
                return {"error": f"Line not found: {line_b_id}"}
            if bond_id in f.bonds:
                return {"error": f"Bond already exists: {bond_id}"}
            bond = CoupleBond(
                bond_id=bond_id,
                line_a_id=line_a_id,
                line_b_id=line_b_id,
                relation=relation,
                strength=max(0.0, min(1.0, strength)),
            )
            f.bonds[bond_id] = bond
            # Promote both lines to COUPLED if they were merely STAGED.
            for lid in (line_a_id, line_b_id):
                line = f.lines.get(lid)
                if line is not None and line.state == LineState.STAGED:
                    line.state = LineState.COUPLED
            self._record_event("bond_added", {
                "field_id": field_id,
                "bond_id": bond_id,
                "line_a_id": line_a_id,
                "line_b_id": line_b_id,
                "relation": relation.value,
                "strength": bond.strength,
            })
            return {
                "field_id": field_id,
                "bond_id": bond_id,
                "line_a_id": line_a_id,
                "line_b_id": line_b_id,
                "relation": relation.value,
                "strength": bond.strength,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single choreographic field cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ChoreographicPhase.NOTATE
            phase_outputs["notate"] = self._phase_notate()
            self._phase = ChoreographicPhase.STAGE
            phase_outputs["stage"] = self._phase_stage()
            self._phase = ChoreographicPhase.COUPLE
            phase_outputs["couple"] = self._phase_couple()
            self._phase = ChoreographicPhase.FLOW
            phase_outputs["flow"] = self._phase_flow()
            self._phase = ChoreographicPhase.RESOLVE
            phase_outputs["resolve"] = self._phase_resolve()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_notate(self) -> Dict[str, Any]:
        """Notate phase: generate waypoints for entities that have no line yet."""
        notated = 0
        for f in self._fields.values():
            for line in f.lines.values():
                # Skip lines that already have waypoints notated.
                if line.waypoints:
                    continue
                line.waypoints = self._notate_line(line)
                line.current_step = 0.0
                line.state = LineState.NOTATED
                notated += 1
                f.total_notated += 1
        self._stats["total_notated"] += notated
        self._record_event("phase_notate", {"notated": notated})
        return {"notated": notated}

    def _phase_stage(self) -> Dict[str, Any]:
        """Stage phase: place entities at their starting positions on the field."""
        staged = 0
        for f in self._fields.values():
            # Spread entities across the field on a regular grid of starting
            # positions so no two start on top of one another.
            entities = list(f.lines.values())
            n = max(1, len(entities))
            for i, line in enumerate(entities):
                if line.state not in (LineState.NOTATED,):
                    continue
                if not line.waypoints:
                    continue
                start = line.waypoints[0]
                # Offset by an indexed spacing so staged entities do not stack.
                offset_x = (i - (n - 1) / 2.0) * self._STAGE_DEFAULT_SPACING
                pos = (
                    max(0.0, min(1.0, start[0] + offset_x)),
                    max(0.0, min(1.0, start[1])),
                )
                f.field_position[line.entity_id] = pos
                line.state = LineState.STAGED
                staged += 1
                f.total_staged += 1
        self._stats["total_staged"] += staged
        self._record_event("phase_stage", {"staged": staged})
        return {"staged": staged}

    def _phase_couple(self) -> Dict[str, Any]:
        """Couple phase: synthesize bonds between nearby entities that lack them."""
        coupled = 0
        for f in self._fields.values():
            if len(f.bonds) >= self._COUPLE_MAX_BONDS:
                continue
            # Find lines that are STAGED but not yet COUPLED.
            candidates = [
                line for line in f.lines.values()
                if line.state in (LineState.STAGED, LineState.NOTATED)
            ]
            random.shuffle(candidates)
            used: set = set()
            for i in range(len(candidates)):
                if len(f.bonds) >= self._COUPLE_MAX_BONDS:
                    break
                if i in used:
                    continue
                a = candidates[i]
                # Find the nearest other candidate by current field position.
                best_j = -1
                best_dist = float("inf")
                a_pos = f.field_position.get(a.entity_id, a.position())
                for j in range(i + 1, len(candidates)):
                    if j in used:
                        continue
                    b = candidates[j]
                    b_pos = f.field_position.get(b.entity_id, b.position())
                    d = (a_pos[0] - b_pos[0]) ** 2 + (a_pos[1] - b_pos[1]) ** 2
                    if d < best_dist:
                        best_dist = d
                        best_j = j
                if best_j < 0:
                    continue
                b = candidates[best_j]
                relation = self._pick_relation(a, b)
                strength = 0.3 + (1.0 - min(1.0, best_dist)) * 0.5
                bond_id = f"bond_{a.line_id}_{b.line_id}_{self._cycle_count}"
                bond = CoupleBond(
                    bond_id=bond_id,
                    line_a_id=a.line_id,
                    line_b_id=b.line_id,
                    relation=relation,
                    strength=max(0.0, min(1.0, strength)),
                )
                f.bonds[bond_id] = bond
                a.state = LineState.COUPLED
                b.state = LineState.COUPLED
                used.add(i)
                used.add(best_j)
                coupled += 1
                f.total_coupled += 1
        self._stats["total_coupled"] += coupled
        self._record_event("phase_couple", {"coupled": coupled})
        return {"coupled": coupled}

    def _phase_flow(self) -> Dict[str, Any]:
        """Flow phase: advance every line one step along its waypoints."""
        flowed = 0
        for f in self._fields.values():
            # Promote STAGED/COUPLED lines to FLOWING on first flow tick.
            for line in f.lines.values():
                if line.state in (LineState.STAGED, LineState.COUPLED, LineState.NOTATED):
                    if line.waypoints:
                        line.state = LineState.FLOWING
            # First pass: advance each flowing line by the step size, scaled
            # by the line's movement quality.
            for line in f.lines.values():
                if line.state != LineState.FLOWING:
                    continue
                step = self._quality_step(line.quality)
                line.current_step += step
                flowed += 1
                f.total_flowed += 1
            # Second pass: apply coupling so partner lines adjust toward one
            # another based on the bond relation and strength.
            self._apply_coupling(f)
            # Sync field_position from line progress.
            for line in f.lines.values():
                if line.state == LineState.SETTLED:
                    continue
                pos = line.position()
                f.field_position[line.entity_id] = pos
        self._stats["total_flowed"] += flowed
        self._record_event("phase_flow", {"flowed": flowed})
        return {"flowed": flowed}

    def _phase_resolve(self) -> Dict[str, Any]:
        """Resolve phase: settle lines that have reached their end."""
        settled = 0
        for f in self._fields.values():
            for line in f.lines.values():
                if line.state != LineState.FLOWING:
                    continue
                progress = self._line_progress(line)
                if progress >= self._RESOLVE_COMPLETION_THRESHOLD:
                    line.current_step = max(0.0, float(len(line.waypoints) - 1))
                    line.state = LineState.SETTLED
                    # Snap final field position to the last waypoint.
                    if line.waypoints:
                        wp = line.waypoints[-1]
                        f.field_position[line.entity_id] = (wp[0], wp[1])
                    settled += 1
                    f.total_settled += 1
        self._stats["total_settled"] += settled
        self._record_event("phase_resolve", {"settled": settled})
        return {"settled": settled}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _notate_line(self, line: MovementLine) -> List[List[float]]:
        """Generate a notated trajectory of waypoints for a movement line."""
        waypoints: List[List[float]] = []
        # Each line begins at a random field entry point and threads through
        # a sequence of waypoints that bend across the field. The shape of
        # the bend depends on the movement quality.
        start_x = random.uniform(0.05, 0.25)
        start_y = random.uniform(0.05, 0.95)
        waypoints.append([start_x, start_y])
        for k in range(1, self._NOTATE_WAYPOINTS):
            frac = k / float(self._NOTATE_WAYPOINTS)
            base_x = start_x + frac * (0.95 - start_x)
            # Quality shapes the vertical drift of the line through the field.
            if line.quality == MovementQuality.FLOWING:
                bend = 0.15 * math_sin(k)
            elif line.quality == MovementQuality.STACCATO:
                bend = 0.25 if k % 2 == 0 else -0.25
            elif line.quality == MovementQuality.SUSPENDED:
                bend = 0.05 * (k % 3)
            elif line.quality == MovementQuality.PERCUSSIVE:
                bend = 0.3 * (1 if k % 2 == 0 else -1)
            else:  # VIBRATORY
                bend = 0.08 * math_sin(k * 3.0)
            y = max(0.02, min(0.98, start_y + bend + (frac - 0.5) * 0.2))
            waypoints.append([round(base_x, 4), round(y, 4)])
        return waypoints

    def _quality_step(self, quality: MovementQuality) -> float:
        """Scale the base flow step size by the movement quality's texture."""
        # Flowing moves steadily; suspended moves slowly; percussive moves in
        # bursts; staccato moves in clipped ticks; vibratory moves in jitter.
        scale = {
            MovementQuality.FLOWING: 1.0,
            MovementQuality.STACCATO: 0.85,
            MovementQuality.SUSPENDED: 0.5,
            MovementQuality.PERCUSSIVE: 1.2,
            MovementQuality.VIBRATORY: 0.7,
        }.get(quality, 1.0)
        return self._FLOW_STEP_SIZE * scale

    def _pick_relation(self, a: MovementLine, b: MovementLine) -> CoupleRelation:
        """Pick a couple relation based on the two lines' qualities."""
        # Same quality tends toward unison; opposite textures tend toward
        # counterpoint; flowing pairings favor lead_follow; mirrors arise
        # when both lines sweep across the field symmetrically.
        if a.quality == b.quality:
            if a.quality == MovementQuality.FLOWING:
                return CoupleRelation.LEAD_FOLLOW
            return CoupleRelation.UNISON
        if {a.quality, b.quality} == {MovementQuality.FLOWING,
                                      MovementQuality.PERCUSSIVE}:
            return CoupleRelation.COUNTERPOINT
        if MovementQuality.SUSPENDED in (a.quality, b.quality):
            return CoupleRelation.MIRROR
        return CoupleRelation.COUNTERPOINT

    def _apply_coupling(self, f: ChoreographicField) -> None:
        """Adjust coupled lines toward their partners based on bond relation."""
        if not f.bonds:
            return
        # Collect the desired step adjustments per line so we can apply them
        # in a single pass after every bond has been evaluated.
        adjustments: Dict[str, float] = {lid: 0.0 for lid in f.lines}
        for bond in f.bonds.values():
            a = f.lines.get(bond.line_a_id)
            b = f.lines.get(bond.line_b_id)
            if a is None or b is None:
                continue
            if a.state != LineState.FLOWING or b.state != LineState.FLOWING:
                continue
            # Compute the gap in progress between the two lines.
            gap = self._line_progress(b) - self._line_progress(a)
            pull = bond.strength * 0.5
            if bond.relation == CoupleRelation.LEAD_FOLLOW:
                # The follower (b) tracks the leader (a) with a delay.
                adjustments[bond.line_b_id] += (self._line_progress(a) - gap * 0.0) * 0.0
                # Translate the gap into a step adjustment so b catches up.
                adjustments[bond.line_b_id] += gap * pull
                adjustments[bond.line_a_id] -= gap * pull * 0.25
            elif bond.relation == CoupleRelation.MIRROR:
                # Mirrored lines are pulled toward equal progress.
                adjustments[bond.line_a_id] += gap * pull
                adjustments[bond.line_b_id] -= gap * pull
            elif bond.relation == CoupleRelation.UNISON:
                # Unison locks the two lines tightly to the same progress.
                adjustments[bond.line_a_id] += gap * pull * 1.2
                adjustments[bond.line_b_id] -= gap * pull * 1.2
            elif bond.relation == CoupleRelation.COUNTERPOINT:
                # Counterpoint allows independence but nudges softly so the
                # voices remain in dialogue rather than drifting apart.
                adjustments[bond.line_a_id] += gap * pull * 0.3
                adjustments[bond.line_b_id] -= gap * pull * 0.3
        # Apply collected adjustments to current_step.
        for lid, adj in adjustments.items():
            if adj == 0.0:
                continue
            line = f.lines.get(lid)
            if line is None or not line.waypoints:
                continue
            max_step = float(len(line.waypoints) - 1)
            line.current_step = max(0.0, min(max_step, line.current_step + adj))

    def _line_progress(self, line: MovementLine) -> float:
        """Return normalized progress along a line's waypoints, 0.0 to 1.0."""
        if not line.waypoints:
            return 0.0
        if len(line.waypoints) == 1:
            return 1.0
        max_step = float(len(line.waypoints) - 1)
        return max(0.0, min(1.0, line.current_step / max_step))

    def _compute_coherence(self, f: ChoreographicField) -> FieldCoherence:
        """Compute the coherence band for a single field."""
        lines = list(f.lines.values())
        if not lines:
            return FieldCoherence.DISPERSED
        # Coherence rises with the share of lines that are coupled and the
        # closeness of all flowing lines' progress to one another.
        coupled_share = 0.0
        for line in lines:
            if line.state in (LineState.COUPLED, LineState.FLOWING, LineState.SETTLED):
                # Lines count as coupled if they appear in at least one bond.
                if any(
                    line.line_id in (b.line_a_id, b.line_b_id) for b in f.bonds.values()
                ):
                    coupled_share += 1.0
        coupled_share = coupled_share / max(1, len(lines))
        progresses = [self._line_progress(line) for line in lines]
        if not progresses:
            return FieldCoherence.DISPERSED
        spread = max(progresses) - min(progresses)
        settled_share = sum(
            1 for line in lines if line.state == LineState.SETTLED
        ) / max(1, len(lines))
        if settled_share >= 0.8:
            return FieldCoherence.HARMONIZED
        if coupled_share >= 0.6 and spread <= 0.3:
            return FieldCoherence.COHERENT
        if coupled_share >= 0.3 or f.bonds:
            return FieldCoherence.COORDINATING
        return FieldCoherence.DISPERSED

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "fields": len(self._fields),
                "stats": dict(self._stats),
            }

    def get_field_state(self, field_id: str) -> Dict[str, Any]:
        with self._global_lock:
            f = self._fields.get(field_id)
            if f is None:
                return {"error": f"Field not found: {field_id}"}
            return {
                "field_id": field_id,
                "lines_count": len(f.lines),
                "bonds_count": len(f.bonds),
                "coherence": f.coherence.value,
                "total_notated": f.total_notated,
                "total_staged": f.total_staged,
                "total_coupled": f.total_coupled,
                "total_flowed": f.total_flowed,
                "total_settled": f.total_settled,
            }

    def get_lines(self, field_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            f = self._fields.get(field_id)
            if f is None:
                return {"error": f"Field not found: {field_id}"}
            lines = sorted(
                f.lines.values(),
                key=lambda l: l.created_at,
                reverse=True,
            )[:limit]
            return {
                "field_id": field_id,
                "lines": [
                    {
                        "line_id": l.line_id,
                        "entity_id": l.entity_id,
                        "quality": l.quality.value,
                        "state": l.state.value,
                        "waypoints": l.waypoints,
                        "current_step": l.current_step,
                        "progress": self._line_progress(l),
                        "position": list(f.field_position.get(l.entity_id, l.position())),
                    }
                    for l in lines
                ],
            }

    def get_bonds(self, field_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            f = self._fields.get(field_id)
            if f is None:
                return {"error": f"Field not found: {field_id}"}
            bonds = sorted(
                f.bonds.values(),
                key=lambda b: b.created_at,
                reverse=True,
            )[:limit]
            return {
                "field_id": field_id,
                "bonds": [
                    {
                        "bond_id": b.bond_id,
                        "line_a_id": b.line_a_id,
                        "line_b_id": b.line_b_id,
                        "relation": b.relation.value,
                        "strength": b.strength,
                    }
                    for b in bonds
                ],
            }

    def get_field_coherence(self, field_id: str) -> Dict[str, Any]:
        with self._global_lock:
            f = self._fields.get(field_id)
            if f is None:
                return {"error": f"Field not found: {field_id}"}
            # Recompute on read so the coherence reflects the latest field state.
            f.coherence = self._compute_coherence(f)
            lines = list(f.lines.values())
            progresses = [self._line_progress(l) for l in lines]
            spread = (max(progresses) - min(progresses)) if progresses else 0.0
            settled = sum(1 for l in lines if l.state == LineState.SETTLED)
            coupled = sum(
                1 for l in lines
                if any(l.line_id in (b.line_a_id, b.line_b_id) for b in f.bonds.values())
            )
            return {
                "field_id": field_id,
                "coherence": f.coherence.value,
                "lines": len(lines),
                "bonds": len(f.bonds),
                "coupled_lines": coupled,
                "settled_lines": settled,
                "progress_spread": spread,
                "avg_progress": (
                    sum(progresses) / len(progresses) if progresses else 0.0
                ),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic fields and entities, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_fields()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_fields(self) -> None:
        """Seed a small set of synthetic fields with varied entities."""
        seed_fields = ["sim_field_alpha", "sim_field_beta", "sim_field_gamma"]
        for field_id in seed_fields:
            if field_id not in self._fields:
                self.register_field(field_id)
        # Seed entities of varying movement qualities onto each field.
        seed_entities = [
            ("sim_field_alpha", "sim_dancer_a1", MovementQuality.FLOWING),
            ("sim_field_alpha", "sim_dancer_a2", MovementQuality.PERCUSSIVE),
            ("sim_field_alpha", "sim_dancer_a3", MovementQuality.SUSPENDED),
            ("sim_field_beta", "sim_dancer_b1", MovementQuality.STACCATO),
            ("sim_field_beta", "sim_dancer_b2", MovementQuality.VIBRATORY),
            ("sim_field_gamma", "sim_dancer_g1", MovementQuality.FLOWING),
            ("sim_field_gamma", "sim_dancer_g2", MovementQuality.FLOWING),
            ("sim_field_gamma", "sim_dancer_g3", MovementQuality.STACCATO),
        ]
        for field_id, entity_id, quality in seed_entities:
            f = self._fields.get(field_id)
            if f is None:
                continue
            line_id = f"line_{entity_id}_{field_id}"
            if line_id not in f.lines:
                self.add_entity(field_id, entity_id, quality)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._fields.clear()
            self._events_log.clear()
            self._phase = ChoreographicPhase.NOTATE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}


# -----------------------------------------------------------------------------
# Local math helpers (avoid importing math module to keep the dependency
# surface identical to the reference engine file).
# -----------------------------------------------------------------------------

def math_sin(x: float) -> float:
    """Approximate sine via a Taylor-series expansion sufficient for waypoint bends."""
    # Reduce x into [-pi, pi] for accuracy.
    two_pi = 6.283185307179586
    x = x - two_pi * round(x / two_pi)
    return x - (x ** 3) / 6.0 + (x ** 5) / 120.0 - (x ** 7) / 5040.0
