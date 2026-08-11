"""
SparkLabs Engine - Emergent Semantics Weaver"""

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

class WeaverPhase(Enum):
    """Phases of the emergent semantics weaving cycle."""
    GATHER = "gather"            # collect raw low-level signals
    CLUSTER = "cluster"          # group co-occurring signals into candidate motifs
    STITCH = "stitch"            # connect related motifs into semantic threads
    BIND = "bind"                # bind stable threads into the narrative fabric
    RELEASE = "release"          # emit the semantic map and dissolve decayed motifs


class SignalKind(Enum):
    """The kind of low-level signal the world produces."""
    SPATIAL = "spatial"          # movement or position
    AUDITORY = "auditory"        # sound
    THERMAL = "thermal"          # temperature
    LINGUISTIC = "linguistic"    # speech or text
    TEMPORAL = "temporal"        # timing
    AFFECTIVE = "affective"      # emotion
    MATERIAL = "material"        # object state


class MotifState(Enum):
    """State of an individual semantic motif."""
    CANDIDATE = "candidate"      # signals grouped, not yet confirmed
    COHERENT = "coherent"        # motif is coherent enough to be stitched
    STABLE = "stable"            # motif is bound into the narrative fabric
    DECAYING = "decaying"        # motif is losing coherence
    DISSOLVED = "dissolved"      # motif has fallen apart, signals released


class ThreadStrength(Enum):
    """How tightly a semantic thread is woven."""
    TENUOUS = "tenuous"          # barely connected
    LOOSE = "loose"              # weakly connected
    BOUND = "bound"              # connected and holding
    TAUT = "taut"                # strongly connected
    WOVEN = "woven"              # bound into the fabric


class WeaverState(Enum):
    """The overall state of the weaver."""
    GATHERING = "gathering"      # collecting signals
    CLUSTERING = "clustering"    # forming motifs
    STITCHING = "stitching"      # forming threads
    BINDING = "binding"          # binding into fabric
    WOVEN = "woven"              # fabric is woven
    FRAYING = "fraying"          # fabric is coming undone


class WeaverVitality(Enum):
    """The overall vitality of the semantic weaving ecosystem."""
    SILENT = "silent"            # no signals, no motifs
    WHISPERING = "whispering"    # a few signals, no fabric yet
    WEAVING = "weaving"          # healthy motif and thread formation
    RESONANT = "resonant"        # fabric is rich and salient
    TANGLED = "tangled"          # too many motifs, over-clustered
    UNRAVELING = "unraveling"    # coherence collapsing across the board


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RawSignal:
    """A raw low-level signal produced by the world."""
    signal_id: str
    kind: SignalKind
    location: str
    value: float = 0.5                   # 0.0-1.0, how strong the signal is
    note: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class SemanticMotif:
    """A cluster of co-occurring signals forming a candidate semantic motif."""
    motif_id: str
    member_signals: List[str] = field(default_factory=list)
    coherence: float = 0.0               # 0.0-1.0, how tightly the signals agree
    state: MotifState = MotifState.CANDIDATE
    label: str = ""
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class SemanticThread:
    """A stitched thread of related motifs."""
    thread_id: str
    motif_ids: List[str] = field(default_factory=list)
    strength: ThreadStrength = ThreadStrength.TENUOUS
    salience: float = 0.0                 # 0.0-1.0, how salient the thread is
    label: str = ""
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class WeaverCycleResult:
    """Structured result of a single weaver cycle."""
    cycle_count: int
    phase: str
    phase_outputs: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Weaver
# =============================================================================

class EngineEmergentSemanticsWeaver:
    """
    Thread-safe singleton orchestrating emergent semantic weaving.

    Usage:
        weaver = EngineEmergentSemanticsWeaver.get_instance()
        weaver.emit_signal("s1", "linguistic", "tavern", 0.8, "whispered threat")
        weaver.cycle()
        smap = weaver.get_semantic_map()
    """

    _instance: Optional["EngineEmergentSemanticsWeaver"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Tuning constants
    _MAX_SIGNALS = 300
    _MAX_MOTIFS = 64
    _MAX_THREADS = 32
    _MAX_FABRIC = 128
    _MAX_EVENTS = 200
    _COHERENCE_THRESHOLD = 0.5
    _SALIENCE_THRESHOLD = 0.6
    _DECAY_THRESHOLD = 0.15
    _DECAY_RATE = 0.05
    _MIN_MOTIF_SIGNALS = 2

    def __init__(self) -> None:
        self._signals: Deque[RawSignal] = deque(maxlen=self._MAX_SIGNALS)
        self._motifs: Dict[str, SemanticMotif] = {}
        self._threads: Dict[str, SemanticThread] = {}
        self._fabric: Dict[str, dict] = {}
        self._absorbed_signal_ids: set = set()
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._cycle_count: int = 0
        self._current_phase: WeaverPhase = WeaverPhase.GATHER
        self._state: WeaverState = WeaverState.GATHERING
        self._uptime_started_at: float = time.time()
        self._stats: Dict[str, Any] = self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineEmergentSemanticsWeaver":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> Dict[str, Any]:
        stats = {
            "cycles_completed": 0,
            "signals_gathered": 0,
            "motifs_clustered": 0,
            "motifs_dissolved": 0,
            "threads_stitched": 0,
            "threads_bound": 0,
            "fabric_entries": 0,
            "mean_coherence": 0.0,
            "mean_salience": 0.0,
            "last_cycle_at": None,
            "uptime_started_at": self._uptime_started_at,
            "vitality": WeaverVitality.SILENT.value,
            "current_state": WeaverState.GATHERING.value,
            "last_cycle_time_ms": 0.0,
        }
        return stats

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            self._stats[key] = value

    def _recompute_means(self) -> None:
        # Mean coherence across all active motifs.
        if self._motifs:
            coherences = [m.coherence for m in self._motifs.values()]
            self._stats["mean_coherence"] = sum(coherences) / len(coherences)
        else:
            self._stats["mean_coherence"] = 0.0
        # Mean salience across all threads.
        if self._threads:
            saliences = [t.salience for t in self._threads.values()]
            self._stats["mean_salience"] = sum(saliences) / len(saliences)
        else:
            self._stats["mean_salience"] = 0.0
        self._stats["fabric_entries"] = len(self._fabric)

    def _derive_vitality(self) -> WeaverVitality:
        motif_count = len(self._motifs)
        thread_count = len(self._threads)
        fabric_count = len(self._fabric)
        mean_coherence = self._stats.get("mean_coherence", 0.0)
        mean_salience = self._stats.get("mean_salience", 0.0)
        if fabric_count == 0 and thread_count == 0 and motif_count == 0:
            return WeaverVitality.SILENT
        if fabric_count > 0 and mean_salience > 0.7:
            return WeaverVitality.RESONANT
        if motif_count >= self._MAX_MOTIFS * 0.8:
            return WeaverVitality.TANGLED
        if mean_coherence < self._DECAY_THRESHOLD and motif_count > 0:
            return WeaverVitality.UNRAVELING
        if fabric_count > 0:
            return WeaverVitality.WEAVING
        return WeaverVitality.WHISPERING

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Signal Intake
    # -------------------------------------------------------------------------

    def emit_signal(self, signal_id: str, kind: str, location: str,
                    value: float = 0.5, note: str = "") -> Dict[str, Any]:
        """Emit a raw low-level signal into the weaver."""
        with self._global_lock:
            if any(s.signal_id == signal_id for s in self._signals):
                return {"error": f"Signal already exists: {signal_id}"}
            try:
                signal_kind = SignalKind(kind)
            except ValueError:
                return {"error": f"Invalid signal kind: {kind}"}
            signal = RawSignal(
                signal_id=signal_id,
                kind=signal_kind,
                location=location,
                value=max(0.0, min(1.0, value)),
                note=note,
            )
            self._signals.append(signal)
            self._stats["signals_gathered"] = (
                self._stats.get("signals_gathered", 0) + 1
            )
            self._record_event("signal_emitted", {
                "signal_id": signal_id,
                "kind": signal_kind.value,
                "location": location,
                "value": signal.value,
            })
            return {
                "signal_id": signal_id,
                "kind": signal_kind.value,
                "location": location,
                "value": signal.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single emergent semantics weaving cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []

            self._current_phase = WeaverPhase.GATHER
            self._state = WeaverState.GATHERING
            phase_outputs.append(self._phase_gather())

            self._current_phase = WeaverPhase.CLUSTER
            self._state = WeaverState.CLUSTERING
            phase_outputs.append(self._phase_cluster())

            self._current_phase = WeaverPhase.STITCH
            self._state = WeaverState.STITCHING
            phase_outputs.append(self._phase_stitch())

            self._current_phase = WeaverPhase.BIND
            self._state = WeaverState.BINDING
            phase_outputs.append(self._phase_bind())

            self._current_phase = WeaverPhase.RELEASE
            release_out = self._phase_release()
            phase_outputs.append(release_out)
            if release_out.get("dissolved", 0) > 0:
                self._state = WeaverState.FRAYING
            else:
                self._state = WeaverState.WOVEN

            self._cycle_count += 1
            self._recompute_means()
            self._update_stats(
                cycles_completed=self._cycle_count,
                last_cycle_at=time.time(),
                vitality=self._derive_vitality().value,
                current_state=self._state.value,
                last_cycle_time_ms=(time.time() - t0) * 1000.0,
            )
            return {
                "cycle_count": self._cycle_count,
                "phase": self._current_phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_gather(self) -> Dict[str, Any]:
        """Gather phase: collect raw low-level signals from registered sources."""
        gathered = len(self._signals)
        # Inventory available signals by kind.
        kind_counts: Dict[str, int] = {}
        for signal in self._signals:
            kind_counts[signal.kind.value] = (
                kind_counts.get(signal.kind.value, 0) + 1
            )
        self._record_event("phase_gather", {
            "gathered": gathered,
            "kind_counts": kind_counts,
        })
        return {
            "phase": WeaverPhase.GATHER.value,
            "gathered": gathered,
            "kind_counts": kind_counts,
        }

    def _phase_cluster(self) -> Dict[str, Any]:
        """Cluster phase: group co-occurring and recurrent signals into candidate motifs."""
        clustered = 0
        # Group not-yet-absorbed signals by location; co-occurring signals at
        # the same location are candidate motif members.
        by_location: Dict[str, List[RawSignal]] = {}
        for signal in self._signals:
            if signal.signal_id in self._absorbed_signal_ids:
                continue
            by_location.setdefault(signal.location, []).append(signal)
        for location, group in by_location.items():
            if len(group) < self._MIN_MOTIF_SIGNALS:
                # A single signal is not yet a motif; it stays as a raw thread.
                continue
            values = [s.value for s in group]
            spread = max(values) - min(values)
            coherence = max(0.0, min(1.0, 1.0 - spread))
            motif_id = f"motif_{location}_{self._cycle_count}_{clustered}"
            motif = SemanticMotif(
                motif_id=motif_id,
                member_signals=[s.signal_id for s in group],
                coherence=coherence,
                state=MotifState.CANDIDATE,
                label=self._label_motif(group),
                note=f"clustered at {location}",
                created_at=time.time(),
            )
            self._motifs[motif_id] = motif
            for s in group:
                self._absorbed_signal_ids.add(s.signal_id)
            clustered += 1
            if len(self._motifs) >= self._MAX_MOTIFS:
                break
        self._update_stats(
            motifs_clustered=self._stats.get("motifs_clustered", 0) + clustered,
        )
        self._record_event("phase_cluster", {"clustered": clustered})
        return {
            "phase": WeaverPhase.CLUSTER.value,
            "clustered": clustered,
            "motifs_total": len(self._motifs),
        }

    def _phase_stitch(self) -> Dict[str, Any]:
        """Stitch phase: connect related motifs into semantic threads."""
        stitched = 0
        # Group coherent motifs by their dominant location; motifs that
        # co-occur at a location are stitched into a thread.
        motif_groups: Dict[str, List[SemanticMotif]] = {}
        for motif in self._motifs.values():
            if motif.state == MotifState.DISSOLVED:
                continue
            if motif.coherence < self._COHERENCE_THRESHOLD:
                # Not coherent enough to stitch yet; stays a candidate.
                continue
            loc = self._motif_location(motif)
            motif_groups.setdefault(loc, []).append(motif)
        for loc, group in motif_groups.items():
            motif_ids = [m.motif_id for m in group]
            # Skip if a thread already covers exactly these motifs.
            if any(set(t.motif_ids) == set(motif_ids)
                   for t in self._threads.values()):
                continue
            thread_id = f"thread_{loc}_{self._cycle_count}_{stitched}"
            avg_coherence = sum(m.coherence for m in group) / len(group)
            strength = self._classify_strength(avg_coherence, len(group))
            thread = SemanticThread(
                thread_id=thread_id,
                motif_ids=motif_ids,
                strength=strength,
                salience=avg_coherence,
                label=self._label_thread(group, loc),
                note=f"stitched at {loc}",
                created_at=time.time(),
            )
            self._threads[thread_id] = thread
            # Promote stitched motifs to COHERENT.
            for m in group:
                if m.state == MotifState.CANDIDATE:
                    m.state = MotifState.COHERENT
            stitched += 1
            if len(self._threads) >= self._MAX_THREADS:
                break
        self._update_stats(
            threads_stitched=self._stats.get("threads_stitched", 0) + stitched,
        )
        self._record_event("phase_stitch", {"stitched": stitched})
        return {
            "phase": WeaverPhase.STITCH.value,
            "stitched": stitched,
            "threads_total": len(self._threads),
        }

    def _phase_bind(self) -> Dict[str, Any]:
        """Bind phase: bind stable threads into the narrative fabric."""
        bound = 0
        updated = 0
        for thread in self._threads.values():
            # Recompute salience from the current coherence of member motifs.
            member_coherences = [
                self._motifs[mid].coherence
                for mid in thread.motif_ids
                if mid in self._motifs
            ]
            if member_coherences:
                thread.salience = (
                    sum(member_coherences) / len(member_coherences)
                )
            if thread.salience < self._SALIENCE_THRESHOLD:
                continue
            if thread.thread_id in self._fabric:
                # Already bound; refresh its salience in the fabric.
                self._fabric[thread.thread_id]["salience"] = thread.salience
                updated += 1
                continue
            self._fabric[thread.thread_id] = {
                "thread_id": thread.thread_id,
                "motif_ids": list(thread.motif_ids),
                "salience": thread.salience,
                "label": thread.label,
                "strength": thread.strength.value,
                "bound_at": time.time(),
            }
            # Promote the thread and its motifs toward stable.
            thread.strength = ThreadStrength.WOVEN
            for motif_id in thread.motif_ids:
                motif = self._motifs.get(motif_id)
                if motif and motif.state in (MotifState.CANDIDATE,
                                             MotifState.COHERENT):
                    motif.state = MotifState.STABLE
            bound += 1
            if len(self._fabric) >= self._MAX_FABRIC:
                break
        self._update_stats(
            threads_bound=self._stats.get("threads_bound", 0) + bound,
        )
        self._record_event("phase_bind", {"bound": bound, "updated": updated})
        return {
            "phase": WeaverPhase.BIND.value,
            "bound": bound,
            "updated": updated,
            "fabric_total": len(self._fabric),
        }

    def _phase_release(self) -> Dict[str, Any]:
        """Release phase: emit the semantic map and dissolve decayed motifs."""
        dissolved = 0
        released_signals = 0
        # Decay every motif a little each cycle.
        for motif in list(self._motifs.values()):
            motif.coherence = max(0.0, motif.coherence - self._DECAY_RATE)
            if motif.coherence < self._DECAY_THRESHOLD:
                if motif.state != MotifState.DISSOLVED:
                    motif.state = MotifState.DISSOLVED
                    # Release its signals back to raw threads.
                    for sid in motif.member_signals:
                        self._absorbed_signal_ids.discard(sid)
                        released_signals += 1
                    dissolved += 1
        # Drop dissolved motifs from the active dict.
        if dissolved > 0:
            self._motifs = {
                mid: m for mid, m in self._motifs.items()
                if m.state != MotifState.DISSOLVED
            }
            # Weaken threads that lost member motifs.
            for thread in self._threads.values():
                alive = [mid for mid in thread.motif_ids
                         if mid in self._motifs]
                if len(alive) < len(thread.motif_ids):
                    thread.motif_ids = alive
                    if thread.strength != ThreadStrength.TENUOUS:
                        thread.strength = ThreadStrength.TENUOUS
            # Drop threads with no motifs left.
            self._threads = {
                tid: t for tid, t in self._threads.items() if t.motif_ids
            }
        self._update_stats(
            motifs_dissolved=self._stats.get("motifs_dissolved", 0) + dissolved,
        )
        semantic_map = self.get_semantic_map()
        self._record_event("phase_release", {
            "dissolved": dissolved,
            "released_signals": released_signals,
        })
        return {
            "phase": WeaverPhase.RELEASE.value,
            "dissolved": dissolved,
            "released_signals": released_signals,
            "semantic_map": semantic_map,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _motif_location(self, motif: SemanticMotif) -> str:
        """Derive the dominant location of a motif from its member signals."""
        for signal in self._signals:
            if signal.signal_id in motif.member_signals:
                return signal.location
        return "unknown"

    def _classify_strength(self, coherence: float,
                           motif_count: int) -> ThreadStrength:
        """Classify the strength of a stitched thread."""
        score = coherence * 0.6 + min(1.0, motif_count / 3.0) * 0.4
        if score >= 0.8:
            return ThreadStrength.WOVEN
        if score >= 0.6:
            return ThreadStrength.TAUT
        if score >= 0.4:
            return ThreadStrength.BOUND
        if score >= 0.2:
            return ThreadStrength.LOOSE
        return ThreadStrength.TENUOUS

    def _label_motif(self, signals: List[RawSignal]) -> str:
        """Compose a short semantic label for a motif from its signals."""
        kinds = sorted({s.kind.value for s in signals})
        loc = signals[0].location if signals else "unknown"
        return f"{'+'.join(kinds)} @ {loc}"

    def _label_thread(self, motifs: List[SemanticMotif], loc: str) -> str:
        """Compose a short semantic label for a thread."""
        return f"thread of {len(motifs)} motif(s) @ {loc}"

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_motif(self, motif_id: str) -> Dict[str, Any]:
        with self._global_lock:
            motif = self._motifs.get(motif_id)
            if motif is None:
                return {"error": f"Motif not found: {motif_id}"}
            return {
                "motif_id": motif.motif_id,
                "member_signals": list(motif.member_signals),
                "coherence": motif.coherence,
                "state": motif.state.value,
                "label": motif.label,
                "note": motif.note,
                "created_at": motif.created_at,
            }

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        with self._global_lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                return {"error": f"Thread not found: {thread_id}"}
            return {
                "thread_id": thread.thread_id,
                "motif_ids": list(thread.motif_ids),
                "strength": thread.strength.value,
                "salience": thread.salience,
                "label": thread.label,
                "note": thread.note,
                "created_at": thread.created_at,
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._current_phase.value,
                "state": self._state.value,
                "vitality": self._derive_vitality().value,
                "cycle_count": self._cycle_count,
                "motifs": len(self._motifs),
                "threads": len(self._threads),
                "fabric": len(self._fabric),
                "raw_signals": len(self._signals),
                "stats": dict(self._stats),
            }

    def get_semantic_map(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "motifs": [
                    {
                        "motif_id": m.motif_id,
                        "member_signals": list(m.member_signals),
                        "coherence": m.coherence,
                        "state": m.state.value,
                        "label": m.label,
                        "note": m.note,
                        "created_at": m.created_at,
                    }
                    for m in self._motifs.values()
                ],
                "threads": [
                    {
                        "thread_id": t.thread_id,
                        "motif_ids": list(t.motif_ids),
                        "strength": t.strength.value,
                        "salience": t.salience,
                        "label": t.label,
                        "note": t.note,
                        "created_at": t.created_at,
                    }
                    for t in self._threads.values()
                ],
                "fabric": dict(self._fabric),
                "raw_signals": len(self._signals),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic signals, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_signals()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_signals(self) -> None:
        """Seed a small synthetic set of low-level signals across locations."""
        seed_signals = [
            ("sim_sig_1", SignalKind.LINGUISTIC, "sim_tavern", 0.8,
             "whispered threat"),
            ("sim_sig_2", SignalKind.AFFECTIVE, "sim_tavern", 0.7,
             "tension rose"),
            ("sim_sig_3", SignalKind.SPATIAL, "sim_tavern", 0.6,
             "figure shifted closer"),
            ("sim_sig_4", SignalKind.THERMAL, "sim_tavern", 0.5,
             "cold draft"),
            ("sim_sig_5", SignalKind.MATERIAL, "sim_market", 0.6,
             "stall shutter slammed"),
            ("sim_sig_6", SignalKind.AUDITORY, "sim_market", 0.7,
             "shouting vendor"),
            ("sim_sig_7", SignalKind.TEMPORAL, "sim_market", 0.4,
             "bells at dusk"),
            ("sim_sig_8", SignalKind.AFFECTIVE, "sim_market", 0.5,
             "crowd unease"),
        ]
        random.shuffle(seed_signals)
        for signal_id, kind, location, value, note in seed_signals:
            if any(s.signal_id == signal_id for s in self._signals):
                continue
            self.emit_signal(signal_id, kind.value, location, value, note)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._signals.clear()
            self._motifs.clear()
            self._threads.clear()
            self._fabric.clear()
            self._absorbed_signal_ids.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._current_phase = WeaverPhase.GATHER
            self._state = WeaverState.GATHERING
            self._uptime_started_at = time.time()
            self._stats = self._init_stats()
            return {"reset": True}