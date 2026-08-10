"""
SparkLabs Engine - Emergence Pattern Detector"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class EmergencePatternType(Enum):
    """Types of emergent patterns the detector can identify."""
    FLOCKING = "flocking"
    SWARMING = "swarming"
    WAVES = "waves"
    SPIRALS = "spirals"
    CLUSTERS = "clusters"
    DIFFUSION = "diffusion"
    OSCILLATION = "oscillation"
    PHASE_TRANSITION = "phase_transition"
    CASCADE = "cascade"
    UNKNOWN = "unknown"


class DetectionPhase(Enum):
    """Phases of the emergence detection cycle."""
    SAMPLE = "sample"
    DETECT = "detect"
    CLASSIFY = "classify"
    PROPAGATE = "propagate"
    CULTIVATE = "cultivate"


class CultivationAction(Enum):
    """How the engine should respond to a detected pattern."""
    ENCOURAGE = "encourage"     # amplify the pattern
    MONITOR = "monitor"         # observe without intervention
    DAMPEN = "dampen"           # reduce the pattern
    HARNESS = "harness"         # capture for gameplay use
    IGNORE = "ignore"           # not interesting


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EntitySample:
    """A single entity's state at a point in time."""
    entity_id: str
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    state: str
    timestamp: float


@dataclass
class SimulationSnapshot:
    """A snapshot of the simulation state at a point in time."""
    timestamp: float
    entities: List[EntitySample]
    entity_count: int
    avg_velocity: Tuple[float, float, float]
    spatial_spread: float  # standard deviation of positions


@dataclass
class EmergencePattern:
    """A detected emergent pattern."""
    pattern_id: str
    pattern_type: EmergencePatternType
    confidence: float          # 0.0 - 1.0
    entity_ids: List[str]      # entities involved
    centroid: Tuple[float, float, float]  # center of the pattern
    extent: float              # spatial extent (radius)
    detected_at: float
    first_seen_at: float
    last_seen_at: float
    observation_count: int = 1
    cultivation: CultivationAction = CultivationAction.MONITOR
    metrics: Dict[str, float] = field(default_factory=dict)
    description: str = ""


@dataclass
class DetectionStats:
    """Aggregate statistics for the emergence detector."""
    total_cycles: int = 0
    total_snapshots_collected: int = 0
    total_patterns_detected: int = 0
    total_unique_patterns: int = 0
    patterns_by_type: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_pattern_duration_s: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine Emergence Pattern Detector
# =============================================================================

class EngineEmergencePatternDetector:
    """
    Singleton engine module that detects emergent patterns in the
    simulation state.

    The detector runs a 5-phase cycle:
      1. SAMPLE    - Collect simulation state snapshots over time
      2. DETECT    - Run pattern detection algorithms on the samples
      3. CLASSIFY  - Identify which type of emergent pattern was found
      4. PROPAGATE - Track how patterns spread and evolve
      5. CULTIVATE - Decide whether to encourage or dampen each pattern

    The detector turns the engine from a passive simulator into an
    observer of its own emergent behavior.
    """

    _instance: Optional["EngineEmergencePatternDetector"] = None
    _instance_lock = threading.Lock()

    # Number of snapshots to keep for analysis
    SNAPSHOT_HISTORY_SIZE = 30
    # Minimum entities required to detect patterns
    MIN_ENTITIES_FOR_PATTERN = 3
    # Minimum observations before a pattern is considered stable
    MIN_OBSERVATIONS_FOR_STABILITY = 2
    # Distance threshold for clustering (in world units)
    CLUSTER_DISTANCE_THRESHOLD = 10.0
    # Velocity alignment threshold for flocking (dot product)
    FLOCKING_ALIGNMENT_THRESHOLD = 0.7
    # Minimum pattern confidence to report
    MIN_REPORT_CONFIDENCE = 0.4
    # Pattern expiry time (seconds without re-observation)
    PATTERN_EXPIRY_S = 60.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshots: Deque[SimulationSnapshot] = deque(maxlen=self.SNAPSHOT_HISTORY_SIZE)
        self._active_patterns: Dict[str, EmergencePattern] = {}
        self._pattern_history: Deque[EmergencePattern] = deque(maxlen=200)
        self._stats = DetectionStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._entity_registry: Set[str] = set()  # known entity IDs

    @classmethod
    def get_instance(cls) -> "EngineEmergencePatternDetector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Phase 1: SAMPLE - Collect simulation state
    # -------------------------------------------------------------------------

    def record_snapshot(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Record a simulation snapshot from entity states.

        Each entity dict should have: entity_id, position (list of 3 floats),
        velocity (list of 3 floats), state (str).
        """
        with self._lock:
            now = time.time()
            samples: List[EntitySample] = []
            for ent_data in entities:
                try:
                    eid = str(ent_data.get("entity_id", ""))
                    pos = tuple(ent_data.get("position", [0, 0, 0]))
                    vel = tuple(ent_data.get("velocity", [0, 0, 0]))
                    state = str(ent_data.get("state", "idle"))
                    if not eid:
                        continue
                    sample = EntitySample(
                        entity_id=eid,
                        position=(float(pos[0]), float(pos[1]), float(pos[2])),
                        velocity=(float(vel[0]), float(vel[1]), float(vel[2])),
                        state=state,
                        timestamp=now,
                    )
                    samples.append(sample)
                    self._entity_registry.add(eid)
                except (IndexError, ValueError, TypeError):
                    continue

            # Compute aggregate metrics
            avg_vel = self._compute_avg_velocity(samples)
            spread = self._compute_spatial_spread(samples)

            snapshot = SimulationSnapshot(
                timestamp=now,
                entities=samples,
                entity_count=len(samples),
                avg_velocity=avg_vel,
                spatial_spread=spread,
            )
            self._snapshots.append(snapshot)
            self._stats.total_snapshots_collected += 1
            return self._snapshot_to_dict(snapshot)

    def _compute_avg_velocity(self, samples: List[EntitySample]) -> Tuple[float, float, float]:
        if not samples:
            return (0.0, 0.0, 0.0)
        sx = sum(s.velocity[0] for s in samples)
        sy = sum(s.velocity[1] for s in samples)
        sz = sum(s.velocity[2] for s in samples)
        n = len(samples)
        return (sx / n, sy / n, sz / n)

    def _compute_spatial_spread(self, samples: List[EntitySample]) -> float:
        if len(samples) < 2:
            return 0.0
        # Standard deviation of positions (using x,y plane)
        xs = [s.position[0] for s in samples]
        ys = [s.position[1] for s in samples]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        variance = sum((x - cx) ** 2 + (y - cy) ** 2 for x, y in zip(xs, ys)) / len(xs)
        return math.sqrt(variance)

    def _sample_phase(self) -> Dict[str, Any]:
        """Check the latest snapshot."""
        if not self._snapshots:
            return {"snapshot_count": 0, "latest_entities": 0}
        latest = self._snapshots[-1]
        return {
            "snapshot_count": len(self._snapshots),
            "latest_entities": latest.entity_count,
            "latest_spread": round(latest.spatial_spread, 2),
        }

    # -------------------------------------------------------------------------
    # Phase 2: DETECT - Run pattern detection algorithms
    # -------------------------------------------------------------------------

    def _detect_phase(self) -> List[Dict[str, Any]]:
        """Run all pattern detection algorithms on recent snapshots."""
        detected: List[Dict[str, Any]] = []
        if len(self._snapshots) < 2:
            return detected
        latest = self._snapshots[-1]
        if latest.entity_count < self.MIN_ENTITIES_FOR_PATTERN:
            return detected

        # Run each detector
        detected.extend(self._detect_flocking(latest))
        detected.extend(self._detect_clustering(latest))
        detected.extend(self._detect_swarming(latest))
        detected.extend(self._detect_diffusion())
        detected.extend(self._detect_oscillation())
        detected.extend(self._detect_cascade())
        detected.extend(self._detect_phase_transition())
        detected.extend(self._detect_waves())
        detected.extend(self._detect_spirals(latest))

        return detected

    def _detect_flocking(self, snapshot: SimulationSnapshot) -> List[Dict[str, Any]]:
        """Detect flocking: entities moving in similar directions."""
        results: List[Dict[str, Any]] = []
        if len(snapshot.entities) < self.MIN_ENTITIES_FOR_PATTERN:
            return results

        # Group entities by velocity alignment
        entities = snapshot.entities
        aligned_groups: List[List[EntitySample]] = []
        used: Set[str] = set()

        for i, base in enumerate(entities):
            if base.entity_id in used:
                continue
            group = [base]
            used.add(base.entity_id)
            base_vel_mag = self._vec_magnitude(base.velocity)
            if base_vel_mag < 0.1:
                continue  # stationary entity can't flock
            base_dir = self._vec_normalize(base.velocity)

            for j in range(i + 1, len(entities)):
                other = entities[j]
                if other.entity_id in used:
                    continue
                other_vel_mag = self._vec_magnitude(other.velocity)
                if other_vel_mag < 0.1:
                    continue
                other_dir = self._vec_normalize(other.velocity)
                alignment = self._vec_dot(base_dir, other_dir)
                if alignment >= self.FLOCKING_ALIGNMENT_THRESHOLD:
                    # Also check spatial proximity
                    dist = self._vec_distance(base.position, other.position)
                    if dist <= self.CLUSTER_DISTANCE_THRESHOLD * 3:
                        group.append(other)
                        used.add(other.entity_id)

            if len(group) >= self.MIN_ENTITIES_FOR_PATTERN:
                centroid = self._compute_centroid([g.position for g in group])
                avg_alignment = self._compute_avg_alignment(group)
                confidence = min(1.0, 0.4 + 0.15 * len(group) + 0.3 * avg_alignment)
                if confidence >= self.MIN_REPORT_CONFIDENCE:
                    results.append({
                        "pattern_type": EmergencePatternType.FLOCKING.value,
                        "confidence": round(confidence, 3),
                        "entity_ids": [g.entity_id for g in group],
                        "centroid": list(centroid),
                        "extent": self._compute_extent([g.position for g in group]),
                        "metrics": {
                            "avg_alignment": round(avg_alignment, 3),
                            "group_size": len(group),
                        },
                        "description": f"{len(group)} entities moving in coordinated direction (alignment={avg_alignment:.2f})",
                    })
        return results

    def _detect_clustering(self, snapshot: SimulationSnapshot) -> List[Dict[str, Any]]:
        """Detect spatial clusters of entities."""
        results: List[Dict[str, Any]] = []
        if len(snapshot.entities) < self.MIN_ENTITIES_FOR_PATTERN:
            return results

        # Simple distance-based clustering
        entities = snapshot.entities
        clusters: List[List[EntitySample]] = []
        used: Set[str] = set()

        for i, base in enumerate(entities):
            if base.entity_id in used:
                continue
            cluster = [base]
            used.add(base.entity_id)
            for j in range(i + 1, len(entities)):
                other = entities[j]
                if other.entity_id in used:
                    continue
                dist = self._vec_distance(base.position, other.position)
                if dist <= self.CLUSTER_DISTANCE_THRESHOLD:
                    cluster.append(other)
                    used.add(other.entity_id)

            if len(cluster) >= self.MIN_ENTITIES_FOR_PATTERN:
                positions = [c.position for c in cluster]
                centroid = self._compute_centroid(positions)
                extent = self._compute_extent(positions)
                confidence = min(1.0, 0.5 + 0.1 * len(cluster))
                if confidence >= self.MIN_REPORT_CONFIDENCE:
                    results.append({
                        "pattern_type": EmergencePatternType.CLUSTERS.value,
                        "confidence": round(confidence, 3),
                        "entity_ids": [c.entity_id for c in cluster],
                        "centroid": list(centroid),
                        "extent": round(extent, 2),
                        "metrics": {
                            "cluster_size": len(cluster),
                            "density": round(len(cluster) / max(1.0, extent), 3),
                        },
                        "description": f"{len(cluster)} entities clustered within {extent:.1f} units",
                    })
        return results

    def _detect_swarming(self, snapshot: SimulationSnapshot) -> List[Dict[str, Any]]:
        """Detect swarming: dense chaotic clustering with varied velocities."""
        results: List[Dict[str, Any]] = []
        if len(snapshot.entities) < self.MIN_ENTITIES_FOR_PATTERN + 2:
            return results

        # Find clusters first, then check for velocity chaos
        clusters = self._detect_clustering(snapshot)
        for cluster_info in clusters:
            entity_ids = set(cluster_info["entity_ids"])
            cluster_entities = [e for e in snapshot.entities if e.entity_id in entity_ids]
            # Check velocity variance
            if len(cluster_entities) < self.MIN_ENTITIES_FOR_PATTERN:
                continue
            velocities = [self._vec_magnitude(e.velocity) for e in cluster_entities]
            avg_v = sum(velocities) / len(velocities)
            variance = sum((v - avg_v) ** 2 for v in velocities) / len(velocities)
            velocity_std = math.sqrt(variance)
            # Swarming = high density + high velocity variance
            if velocity_std > 0.5 and avg_v > 0.3:
                confidence = min(1.0, 0.5 + 0.2 * velocity_std + 0.1 * len(cluster_entities))
                if confidence >= self.MIN_REPORT_CONFIDENCE:
                    results.append({
                        "pattern_type": EmergencePatternType.SWARMING.value,
                        "confidence": round(confidence, 3),
                        "entity_ids": list(entity_ids),
                        "centroid": cluster_info["centroid"],
                        "extent": cluster_info["extent"],
                        "metrics": {
                            "velocity_std": round(velocity_std, 3),
                            "avg_velocity": round(avg_v, 3),
                            "swarm_size": len(cluster_entities),
                        },
                        "description": f"{len(cluster_entities)} entities swarming chaotically (v_std={velocity_std:.2f})",
                    })
        return results

    def _detect_diffusion(self) -> List[Dict[str, Any]]:
        """Detect diffusion: entities spreading out from a concentrated area."""
        results: List[Dict[str, Any]] = []
        if len(self._snapshots) < 3:
            return results
        recent = list(self._snapshots)[-3:]
        # Check if spatial spread is increasing
        spreads = [s.spatial_spread for s in recent]
        if spreads[0] > 0 and spreads[-1] > spreads[0] * 1.3:
            # Spread is increasing significantly
            increase_ratio = spreads[-1] / max(spreads[0], 0.1)
            confidence = min(1.0, 0.5 + 0.2 * (increase_ratio - 1.0))
            if confidence >= self.MIN_REPORT_CONFIDENCE:
                latest = recent[-1]
                results.append({
                    "pattern_type": EmergencePatternType.DIFFUSION.value,
                    "confidence": round(confidence, 3),
                    "entity_ids": [e.entity_id for e in latest.entities],
                    "centroid": [0.0, 0.0, 0.0],
                    "extent": round(latest.spatial_spread, 2),
                    "metrics": {
                        "spread_increase": round(increase_ratio, 3),
                        "initial_spread": round(spreads[0], 2),
                        "final_spread": round(spreads[-1], 2),
                    },
                    "description": f"Entities diffusing outward (spread {spreads[0]:.1f} -> {spreads[-1]:.1f})",
                })
        return results

    def _detect_oscillation(self) -> List[Dict[str, Any]]:
        """Detect oscillation: periodic state cycling in entity populations."""
        results: List[Dict[str, Any]] = []
        if len(self._snapshots) < 5:
            return results
        recent = list(self._snapshots)[-5:]
        # Check if states are cycling
        # Count state distribution per snapshot
        state_counts_per_snapshot: List[Dict[str, int]] = []
        for snap in recent:
            counts: Dict[str, int] = defaultdict(int)
            for e in snap.entities:
                counts[e.state] += 1
            state_counts_per_snapshot.append(dict(counts))

        # Check if any state count oscillates (goes up and down)
        all_states: Set[str] = set()
        for sc in state_counts_per_snapshot:
            all_states.update(sc.keys())

        for state in all_states:
            counts = [sc.get(state, 0) for sc in state_counts_per_snapshot]
            # Check for oscillation (sign changes in differences)
            if len(counts) < 4:
                continue
            diffs = [counts[i + 1] - counts[i] for i in range(len(counts) - 1)]
            sign_changes = sum(1 for i in range(len(diffs) - 1)
                             if diffs[i] * diffs[i + 1] < 0)
            if sign_changes >= 2 and max(counts) > 0:
                confidence = min(1.0, 0.4 + 0.2 * sign_changes)
                if confidence >= self.MIN_REPORT_CONFIDENCE:
                    results.append({
                        "pattern_type": EmergencePatternType.OSCILLATION.value,
                        "confidence": round(confidence, 3),
                        "entity_ids": [],
                        "centroid": [0.0, 0.0, 0.0],
                        "extent": 0.0,
                        "metrics": {
                            "state": state,
                            "sign_changes": sign_changes,
                            "count_range": f"{min(counts)}-{max(counts)}",
                        },
                        "description": f"State '{state}' oscillating (sign changes: {sign_changes})",
                    })
        return results

    def _detect_cascade(self) -> List[Dict[str, Any]]:
        """Detect cascade: chain reactions propagating through the network."""
        results: List[Dict[str, Any]] = []
        if len(self._snapshots) < 3:
            return results
        recent = list(self._snapshots)[-3:]
        # Check if same-state entities are growing rapidly
        state_growth: Dict[str, List[int]] = defaultdict(list)
        for snap in recent:
            counts: Dict[str, int] = defaultdict(int)
            for e in snap.entities:
                counts[e.state] += 1
            for state, count in counts.items():
                state_growth[state].append(count)

        for state, counts in state_growth.items():
            if len(counts) >= 3 and counts[0] > 0:
                growth_ratio = counts[-1] / counts[0]
                if growth_ratio >= 2.0:
                    confidence = min(1.0, 0.5 + 0.3 * (growth_ratio - 1.0) / 3.0)
                    if confidence >= self.MIN_REPORT_CONFIDENCE:
                        results.append({
                            "pattern_type": EmergencePatternType.CASCADE.value,
                            "confidence": round(confidence, 3),
                            "entity_ids": [],
                            "centroid": [0.0, 0.0, 0.0],
                            "extent": 0.0,
                            "metrics": {
                                "state": state,
                                "growth_ratio": round(growth_ratio, 2),
                                "initial_count": counts[0],
                                "final_count": counts[-1],
                            },
                            "description": f"Cascade in state '{state}' ({counts[0]} -> {counts[-1]}, {growth_ratio:.1f}x)",
                        })
        return results

    def _detect_phase_transition(self) -> List[Dict[str, Any]]:
        """Detect phase transition: sudden collective state change."""
        results: List[Dict[str, Any]] = []
        if len(self._snapshots) < 2:
            return results
        prev = self._snapshots[-2]
        curr = self._snapshots[-1]
        if prev.entity_count == 0 or curr.entity_count == 0:
            return results

        # Count state distributions
        prev_states: Dict[str, int] = defaultdict(int)
        curr_states: Dict[str, int] = defaultdict(int)
        for e in prev.entities:
            prev_states[e.state] += 1
        for e in curr.entities:
            curr_states[e.state] += 1

        all_states = set(prev_states.keys()) | set(curr_states.keys())
        max_shift = 0.0
        shifted_state = ""
        for state in all_states:
            prev_pct = prev_states.get(state, 0) / prev.entity_count
            curr_pct = curr_states.get(state, 0) / curr.entity_count
            shift = abs(curr_pct - prev_pct)
            if shift > max_shift:
                max_shift = shift
                shifted_state = state

        if max_shift >= 0.4:  # 40% of population shifted
            confidence = min(1.0, 0.5 + max_shift)
            if confidence >= self.MIN_REPORT_CONFIDENCE:
                results.append({
                    "pattern_type": EmergencePatternType.PHASE_TRANSITION.value,
                    "confidence": round(confidence, 3),
                    "entity_ids": [],
                    "centroid": [0.0, 0.0, 0.0],
                    "extent": 0.0,
                    "metrics": {
                        "shifted_state": shifted_state,
                        "shift_magnitude": round(max_shift, 3),
                    },
                    "description": f"Phase transition: {max_shift * 100:.0f}% of population shifted to '{shifted_state}'",
                })
        return results

    def _detect_waves(self) -> List[Dict[str, Any]]:
        """Detect waves: propagating oscillations through entity populations."""
        results: List[Dict[str, Any]] = []
        if len(self._snapshots) < 4:
            return results
        recent = list(self._snapshots)[-4:]
        # Check if centroid is moving in a wave pattern
        centroids = [self._compute_centroid([e.position for e in s.entities]) for s in recent]
        if len(centroids) < 4:
            return results
        # Check for back-and-forth movement
        movements = []
        for i in range(len(centroids) - 1):
            dx = centroids[i + 1][0] - centroids[i][0]
            dy = centroids[i + 1][1] - centroids[i][1]
            movements.append((dx, dy))
        if len(movements) >= 3:
            # Check if direction reverses
            direction_changes = 0
            for i in range(len(movements) - 1):
                dot = movements[i][0] * movements[i + 1][0] + movements[i][1] * movements[i + 1][1]
                if dot < 0:
                    direction_changes += 1
            if direction_changes >= 1:
                confidence = min(1.0, 0.5 + 0.2 * direction_changes)
                if confidence >= self.MIN_REPORT_CONFIDENCE:
                    results.append({
                        "pattern_type": EmergencePatternType.WAVES.value,
                        "confidence": round(confidence, 3),
                        "entity_ids": [],
                        "centroid": list(centroids[-1]),
                        "extent": 0.0,
                        "metrics": {
                            "direction_changes": direction_changes,
                            "sample_count": len(recent),
                        },
                        "description": f"Wave pattern detected ({direction_changes} direction reversals)",
                    })
        return results

    def _detect_spirals(self, snapshot: SimulationSnapshot) -> List[Dict[str, Any]]:
        """Detect spiral patterns: rotational movement around attractors."""
        results: List[Dict[str, Any]] = []
        if len(snapshot.entities) < self.MIN_ENTITIES_FOR_PATTERN:
            return results
        if len(self._snapshots) < 3:
            return results

        # Check for rotational velocity (perpendicular to position from centroid)
        recent = list(self._snapshots)[-3:]
        for snap in recent:
            if len(snap.entities) < self.MIN_ENTITIES_FOR_PATTERN:
                continue
            centroid = self._compute_centroid([e.position for e in snap.entities])
            rotation_count = 0
            for e in snap.entities:
                # Vector from centroid to entity (2D for rotation check)
                rel_x = e.position[0] - centroid[0]
                rel_y = e.position[1] - centroid[1]
                rel_mag = math.sqrt(rel_x * rel_x + rel_y * rel_y)
                # Perpendicular (rotational) velocity check
                if rel_mag < 0.1:
                    continue
                # Velocity perpendicular to rel_pos indicates rotation
                rel_norm_x = rel_x / rel_mag
                rel_norm_y = rel_y / rel_mag
                vel_mag = self._vec_magnitude(e.velocity)
                if vel_mag < 0.1:
                    continue
                vel_norm = self._vec_normalize(e.velocity)
                # Cross product (z-component) indicates rotation direction
                cross = rel_norm_x * vel_norm[1] - rel_norm_y * vel_norm[0]
                if abs(cross) > 0.5:  # significant rotational component
                    rotation_count += 1

            if rotation_count >= self.MIN_ENTITIES_FOR_PATTERN:
                confidence = min(1.0, 0.4 + 0.15 * rotation_count)
                if confidence >= self.MIN_REPORT_CONFIDENCE:
                    results.append({
                        "pattern_type": EmergencePatternType.SPIRALS.value,
                        "confidence": round(confidence, 3),
                        "entity_ids": [e.entity_id for e in snap.entities],
                        "centroid": list(centroid),
                        "extent": 0.0,
                        "metrics": {
                            "rotating_entities": rotation_count,
                            "total_entities": len(snap.entities),
                        },
                        "description": f"{rotation_count} entities in rotational motion around centroid",
                    })
                break  # one spiral per cycle is enough
        return results

    # -------------------------------------------------------------------------
    # Phase 3: CLASSIFY - Pattern classification and consolidation
    # -------------------------------------------------------------------------

    def _classify_phase(self, detected: List[Dict[str, Any]]) -> List[EmergencePattern]:
        """Convert detected patterns into EmergencePattern objects."""
        new_patterns: List[EmergencePattern] = []
        now = time.time()

        for det in detected:
            pattern_type_str = det.get("pattern_type", "unknown")
            try:
                ptype = EmergencePatternType(pattern_type_str)
            except ValueError:
                ptype = EmergencePatternType.UNKNOWN

            # Check if this pattern already exists (match by type + entity overlap)
            existing = self._find_matching_pattern(ptype, det.get("entity_ids", []))
            if existing is not None:
                # Reinforce existing pattern
                existing.confidence = max(existing.confidence, det.get("confidence", 0.0))
                existing.observation_count += 1
                existing.last_seen_at = now
                existing.metrics.update(det.get("metrics", {}))
                existing.description = det.get("description", existing.description)
            else:
                # Create new pattern
                pid = f"pat_{int(now * 1000)}_{len(self._active_patterns)}"
                pattern = EmergencePattern(
                    pattern_id=pid,
                    pattern_type=ptype,
                    confidence=det.get("confidence", 0.5),
                    entity_ids=det.get("entity_ids", []),
                    centroid=tuple(det.get("centroid", [0, 0, 0])),
                    extent=det.get("extent", 0.0),
                    detected_at=now,
                    first_seen_at=now,
                    last_seen_at=now,
                    observation_count=1,
                    metrics=det.get("metrics", {}),
                    description=det.get("description", ""),
                )
                self._active_patterns[pid] = pattern
                new_patterns.append(pattern)
                self._stats.total_unique_patterns += 1
                self._stats.patterns_by_type[ptype.value] = \
                    self._stats.patterns_by_type.get(ptype.value, 0) + 1

            self._stats.total_patterns_detected += 1

        return new_patterns

    def _find_matching_pattern(self, ptype: EmergencePatternType,
                                entity_ids: List[str]) -> Optional[EmergencePattern]:
        """Find an existing pattern that matches the type and has entity overlap."""
        if not entity_ids:
            # For non-spatial patterns, match by type only
            for p in self._active_patterns.values():
                if p.pattern_type == ptype:
                    return p
            return None
        new_set = set(entity_ids)
        for p in self._active_patterns.values():
            if p.pattern_type != ptype:
                continue
            if not p.entity_ids:
                continue
            overlap = len(set(p.entity_ids) & new_set)
            if overlap >= len(new_set) * 0.5:
                return p
        return None

    # -------------------------------------------------------------------------
    # Phase 4: PROPAGATE - Track pattern spread and evolution
    # -------------------------------------------------------------------------

    def _propagate_phase(self) -> Dict[str, Any]:
        """Track how patterns spread and expire old ones."""
        now = time.time()
        expired: List[str] = []
        for pid, pattern in list(self._active_patterns.items()):
            # Expire patterns that haven't been seen recently
            if now - pattern.last_seen_at > self.PATTERN_EXPIRY_S:
                # Decay confidence
                pattern.confidence *= 0.7
                if pattern.confidence < 0.1:
                    self._pattern_history.append(pattern)
                    expired.append(pid)
                    continue
            # Decay confidence slightly each cycle
            pattern.confidence *= 0.95

        for pid in expired:
            self._active_patterns.pop(pid, None)

        return {
            "active_patterns": len(self._active_patterns),
            "expired": len(expired),
            "propagated": len(self._active_patterns),
        }

    # -------------------------------------------------------------------------
    # Phase 5: CULTIVATE - Decide how to respond to each pattern
    # -------------------------------------------------------------------------

    def _cultivate_phase(self) -> Dict[str, Any]:
        """Decide whether to encourage or dampen each active pattern."""
        decisions: List[Dict[str, Any]] = []
        for pattern in self._active_patterns.values():
            action = self._decide_cultivation(pattern)
            pattern.cultivation = action
            decisions.append({
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type.value,
                "action": action.value,
                "confidence": pattern.confidence,
                "observations": pattern.observation_count,
            })
        return {
            "decisions": decisions,
            "encouraged": sum(1 for d in decisions if d["action"] == "encourage"),
            "monitored": sum(1 for d in decisions if d["action"] == "monitor"),
            "dampened": sum(1 for d in decisions if d["action"] == "dampen"),
            "harnessed": sum(1 for d in decisions if d["action"] == "harness"),
            "ignored": sum(1 for d in decisions if d["action"] == "ignore"),
        }

    def _decide_cultivation(self, pattern: EmergencePattern) -> CultivationAction:
        """Decide how to respond to a pattern based on its properties."""
        # High confidence + many observations = harness for gameplay
        if pattern.confidence > 0.8 and pattern.observation_count >= 3:
            return CultivationAction.HARNESS
        # High confidence but new = monitor
        if pattern.confidence > 0.7:
            return CultivationAction.MONITOR
        # Medium confidence = monitor
        if pattern.confidence > 0.5:
            return CultivationAction.MONITOR
        # Low confidence but persistent = encourage (might be interesting)
        if pattern.observation_count >= 3:
            return CultivationAction.ENCOURAGE
        # Low confidence and new = ignore
        return CultivationAction.IGNORE

    # -------------------------------------------------------------------------
    # Detection Cycle Orchestration
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single emergence detection cycle.

        Phases: SAMPLE -> DETECT -> CLASSIFY -> PROPAGATE -> CULTIVATE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: SAMPLE
            phase = DetectionPhase.SAMPLE
            sample_info = self._sample_phase()

            # Phase 2: DETECT
            phase = DetectionPhase.DETECT
            detected = self._detect_phase()

            # Phase 3: CLASSIFY
            phase = DetectionPhase.CLASSIFY
            new_patterns = self._classify_phase(detected)

            # Phase 4: PROPAGATE
            phase = DetectionPhase.PROPAGATE
            propagate_info = self._propagate_phase()

            # Phase 5: CULTIVATE
            phase = DetectionPhase.CULTIVATE
            cultivate_info = self._cultivate_phase()

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.total_cycles += 1
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._update_avg_confidence()

            self._active = False

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "sample": sample_info,
                "detected_count": len(detected),
                "new_patterns": len(new_patterns),
                "active_patterns": len(self._active_patterns),
                "propagate": propagate_info,
                "cultivate": cultivate_info,
                "patterns": [self._pattern_to_dict(p) for p in self._active_patterns.values()],
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple detection cycles with synthetic simulation data."""
        with self._lock:
            results = []
            for i in range(max(1, cycles)):
                # Generate synthetic entities with evolving behavior
                self._seed_synthetic_snapshot(i)
                results.append(self.run_cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_stats": self._stats_to_dict(),
            }

    def _seed_synthetic_snapshot(self, cycle_idx: int) -> None:
        """Seed a synthetic snapshot for simulation."""
        entities: List[Dict[str, Any]] = []
        # Create a flock of entities moving together
        if cycle_idx % 3 == 0:
            # Flocking pattern
            base_x = 10.0 + cycle_idx * 2
            base_y = 5.0
            for i in range(6):
                entities.append({
                    "entity_id": f"bird_{i}",
                    "position": [base_x + i * 0.5, base_y + i * 0.3, 5.0],
                    "velocity": [1.0, 0.5, 0.0],
                    "state": "flying",
                })
        elif cycle_idx % 3 == 1:
            # Clustering pattern
            for i in range(5):
                angle = i * (2 * math.pi / 5)
                entities.append({
                    "entity_id": f"npc_{i}",
                    "position": [math.cos(angle) * 3, math.sin(angle) * 3, 0.0],
                    "velocity": [0.0, 0.0, 0.0],
                    "state": "gathering",
                })
        else:
            # Diffusion pattern (spreading out)
            for i in range(8):
                angle = i * (2 * math.pi / 8)
                dist = 2.0 + cycle_idx * 1.5
                entities.append({
                    "entity_id": f"particle_{i}",
                    "position": [math.cos(angle) * dist, math.sin(angle) * dist, 0.0],
                    "velocity": [math.cos(angle) * 0.5, math.sin(angle) * 0.5, 0.0],
                    "state": "spreading",
                })
        self.record_snapshot(entities)

    # -------------------------------------------------------------------------
    # Query and Inspection
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "snapshot_count": len(self._snapshots),
                "active_patterns": len(self._active_patterns),
                "known_entities": len(self._entity_registry),
                "stats": self._stats_to_dict(),
            }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_cycles": self._stats.total_cycles,
            "total_snapshots_collected": self._stats.total_snapshots_collected,
            "total_patterns_detected": self._stats.total_patterns_detected,
            "total_unique_patterns": self._stats.total_unique_patterns,
            "patterns_by_type": dict(self._stats.patterns_by_type),
            "avg_confidence": self._stats.avg_confidence,
            "avg_pattern_duration_s": self._stats.avg_pattern_duration_s,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def list_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            patterns = sorted(self._active_patterns.values(),
                              key=lambda p: p.confidence, reverse=True)
            return [self._pattern_to_dict(p) for p in patterns[:limit]]

    def list_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._pattern_to_dict(p) for p in list(self._pattern_history)[-limit:]]

    def list_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._snapshot_to_dict(s) for s in list(self._snapshots)[-limit:]]

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            p = self._active_patterns.get(pattern_id)
            return self._pattern_to_dict(p) if p else None

    def set_cultivation(self, pattern_id: str, action: str) -> Dict[str, Any]:
        """Manually set the cultivation action for a pattern."""
        with self._lock:
            p = self._active_patterns.get(pattern_id)
            if p is None:
                return {"error": f"Pattern not found: {pattern_id}"}
            try:
                p.cultivation = CultivationAction(action)
            except ValueError:
                return {"error": f"Invalid action: {action}"}
            return self._pattern_to_dict(p)

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            pattern_count = len(self._active_patterns)
            self._snapshots.clear()
            self._active_patterns.clear()
            self._pattern_history.clear()
            self._entity_registry.clear()
            self._stats = DetectionStats()
            self._cycle_count = 0
            return {"reset": True, "cleared_patterns": pattern_count}

    def _update_avg_confidence(self) -> None:
        if not self._active_patterns:
            return
        total = sum(p.confidence for p in self._active_patterns.values())
        self._stats.avg_confidence = round(total / len(self._active_patterns), 3)

    # -------------------------------------------------------------------------
    # Vector math utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _vec_magnitude(v: Tuple[float, float, float]) -> float:
        return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)

    @staticmethod
    def _vec_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        mag = EngineEmergencePatternDetector._vec_magnitude(v)
        if mag < 1e-6:
            return (0.0, 0.0, 0.0)
        return (v[0] / mag, v[1] / mag, v[2] / mag)

    @staticmethod
    def _vec_dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _vec_distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        return EngineEmergencePatternDetector._vec_magnitude(
            (a[0] - b[0], a[1] - b[1], a[2] - b[2])
        )

    @staticmethod
    def _compute_centroid(positions: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        if not positions:
            return (0.0, 0.0, 0.0)
        sx = sum(p[0] for p in positions)
        sy = sum(p[1] for p in positions)
        sz = sum(p[2] for p in positions)
        n = len(positions)
        return (sx / n, sy / n, sz / n)

    @staticmethod
    def _compute_extent(positions: List[Tuple[float, float, float]]) -> float:
        """Compute the spatial extent (max distance from centroid)."""
        if len(positions) < 2:
            return 0.0
        centroid = EngineEmergencePatternDetector._compute_centroid(positions)
        max_dist = 0.0
        for p in positions:
            d = EngineEmergencePatternDetector._vec_distance(p, centroid)
            if d > max_dist:
                max_dist = d
        return max_dist

    def _compute_avg_alignment(self, group: List[EntitySample]) -> float:
        """Compute average pairwise velocity alignment within a group."""
        if len(group) < 2:
            return 1.0
        total = 0.0
        count = 0
        for i in range(len(group)):
            dir_i = self._vec_normalize(group[i].velocity)
            if self._vec_magnitude(dir_i) < 0.1:
                continue
            for j in range(i + 1, len(group)):
                dir_j = self._vec_normalize(group[j].velocity)
                if self._vec_magnitude(dir_j) < 0.1:
                    continue
                total += self._vec_dot(dir_i, dir_j)
                count += 1
        return total / count if count > 0 else 0.0

    # -------------------------------------------------------------------------
    # Serialization helpers
    # -------------------------------------------------------------------------

    def _snapshot_to_dict(self, s: SimulationSnapshot) -> Dict[str, Any]:
        return {
            "timestamp": s.timestamp,
            "entity_count": s.entity_count,
            "avg_velocity": list(s.avg_velocity),
            "spatial_spread": round(s.spatial_spread, 2),
            "entities": [
                {
                    "entity_id": e.entity_id,
                    "position": list(e.position),
                    "velocity": list(e.velocity),
                    "state": e.state,
                }
                for e in s.entities[:10]  # limit for serialization
            ],
        }

    def _pattern_to_dict(self, p: EmergencePattern) -> Dict[str, Any]:
        return {
            "pattern_id": p.pattern_id,
            "pattern_type": p.pattern_type.value,
            "confidence": round(p.confidence, 3),
            "entity_ids": p.entity_ids[:20],  # limit
            "centroid": list(p.centroid),
            "extent": round(p.extent, 2),
            "detected_at": p.detected_at,
            "first_seen_at": p.first_seen_at,
            "last_seen_at": p.last_seen_at,
            "observation_count": p.observation_count,
            "cultivation": p.cultivation.value,
            "metrics": p.metrics,
            "description": p.description,
        }
