"""
SparkLabs Agent - Causal Blame Arbiter

The AgentCausalBlameArbiter arbitrates causal blame attribution for
narrative events. When something consequential happens in the story, this
agent traces the causal chain backward, weighs each contributor's share,
and issues a structured blame assignment that respects intent, foresight,
negligence, and proximate cause. It distinguishes moral blame (you meant
it) from causal contribution (you made it possible) from negligence blame
(you should have seen it). The output is a defensible blame ledger that
the story can lean on so that accountability feels earned rather than
arbitrary.

A story that assigns blame arbitrarily feels unfair; a story that assigns
blame along a traceable causal chain feels just - even when the verdict is
harsh. The arbiter exists to make accountability legible.

Architecture:
  GATHER      ->  TRACE     ->  WEIGH      ->  ARBITRATE  ->  RECORD
  (collect     (build the    (score each    (convert the   (write the
   the event   causal chain  contributor    weights into   assignment to
   and its     backward,     on intent,     a blame        the ledger,
   candidate   marking each  foresight,     assignment     return the
   contributors) link's       negligence,    that sums to   verdict)
                strength)     and proximate  1.0 across
                              strength)      contributors)

Thread-safe singleton: use get_instance().
"""

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

class ArbiterPhase(Enum):
    """Phases of the causal blame arbitration cycle."""
    GATHER = "gather"          # collect the event and its candidate contributors
    TRACE = "trace"            # build the causal chain backward
    WEIGH = "weigh"            # score each contributor on the four dimensions
    ARBITRATE = "arbitrate"    # convert weights into a blame assignment
    RECORD = "record"          # write the assignment to the ledger


class BlameDimension(Enum):
    """Dimensions along which a contributor is weighed."""
    INTENT = "intent"                          # did they mean it?
    FORESIGHT = "foresight"                    # could they see it coming?
    NEGLIGENCE = "negligence"                  # should they have seen it coming?
    PROXIMATE_STRENGTH = "proximate_strength"  # how directly did they cause it?


class BlameFlavor(Enum):
    """The flavor of blame assigned to a contributor."""
    MORAL = "moral"            # they meant it
    CAUSAL = "causal"          # they made it possible
    NEGLIGENT = "negligent"    # they should have seen it
    INHERENT = "inherent"      # it was in their nature
    ACCIDENTAL = "accidental"  # no one meant it


class ChainLinkStrength(Enum):
    """Strength of a link in the causal chain."""
    DIRECT = "direct"          # the link is the proximate cause
    STRONG = "strong"          # the link is a clear contributor
    MODERATE = "moderate"      # the link plausibly contributed
    WEAK = "weak"              # the link barely contributed
    TENUOUS = "tenuous"        # the link is only notionally present


class VerdictState(Enum):
    """State of an event moving through arbitration."""
    PENDING = "pending"        # registered, awaiting the cycle
    TRACED = "traced"          # causal chain built
    WEIGHED = "weighed"        # contributors scored
    ARBITRATED = "arbitrated"  # blame shares computed
    RECORDED = "recorded"      # written to the ledger
    OVERTURNED = "overturned"  # a later arbitration overturned the verdict


class ArbiterVitality(Enum):
    """Overall vitality of the arbiter."""
    IDLE = "idle"              # no events pending
    DELIBERATING = "deliberating"  # a few events working through the cycle
    ACTIVE = "active"          # steady flow of events
    BACKLOGGED = "backlogged"  # events piling up faster than they resolve
    SATURATED = "saturated"    # cannot keep up, events overflowing


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Contributor:
    """A candidate contributor to a narrative event."""
    contributor_id: str
    role: str
    intent_score: float = 0.0           # 0.0-1.0, did they mean it
    foresight_score: float = 0.0        # 0.0-1.0, could they foresee it
    negligence_score: float = 0.0       # 0.0-1.0, should they have foreseen it
    proximate_strength: float = 0.0     # 0.0-1.0, how directly causal
    note: str = ""


@dataclass
class CausalLink:
    """A single link in the causal chain leading to the event."""
    from_id: str
    to_id: str
    strength: ChainLinkStrength = ChainLinkStrength.MODERATE
    note: str = ""


@dataclass
class BlameAssignment:
    """A single contributor's assigned share of blame."""
    contributor_id: str
    share: float = 0.0                  # 0.0-1.0, normalized to sum to 1.0
    flavor: BlameFlavor = BlameFlavor.CAUSAL
    rationale: str = ""


@dataclass
class ArbiterCycleResult:
    """Summary of a single arbitration cycle."""
    cycle_count: int
    phase: str
    gathered: int = 0
    traced: int = 0
    weighed: int = 0
    arbitrated: int = 0
    recorded: int = 0


# =============================================================================
# Arbiter
# =============================================================================

class AgentCausalBlameArbiter:
    """
    Thread-safe singleton orchestrating causal blame arbitration.

    Usage:
        arbiter = AgentCausalBlameArbiter.get_instance()
        arbiter.register_event("evt1",
            contributors=[{"contributor_id":"c1","role":"initiator",
                "intent_score":0.8,"foresight_score":0.7,
                "negligence_score":0.2,"proximate_strength":0.9,
                "note":"struck the match"}],
            links=[])
        arbiter.cycle()
        verdict = arbiter.get_verdict("evt1")
    """

    _instance: Optional["AgentCausalBlameArbiter"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _MAX_CONTRIBUTORS = 16
    _MAX_CHAIN_DEPTH = 8
    _MAX_EVENTS = 200
    _MAX_LEDGER_ENTRIES = 500

    # Weights for the four blame dimensions when computing a raw blame score.
    _DIMENSION_WEIGHTS = {
        BlameDimension.INTENT: 0.35,
        BlameDimension.FORESIGHT: 0.20,
        BlameDimension.NEGLIGENCE: 0.20,
        BlameDimension.PROXIMATE_STRENGTH: 0.25,
    }

    # Thresholds for flavor classification.
    _MORAL_INTENT_THRESHOLD = 0.6
    _NEGLIGENT_THRESHOLD = 0.6
    _ACCIDENTAL_THRESHOLD = 0.2
    _CAUSAL_PROXIMATE_THRESHOLD = 0.7

    # Vitality thresholds (pending events).
    _VITALITY_ACTIVE_THRESHOLD = 3
    _VITALITY_BACKLOGGED_THRESHOLD = 8
    _VITALITY_SATURATED_THRESHOLD = 16

    def __init__(self) -> None:
        self._events: Dict[str, dict] = {}
        self._ledger: Dict[str, list] = {}  # event_id -> list of assignment dicts
        self._phase: ArbiterPhase = ArbiterPhase.GATHER
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentCausalBlameArbiter":
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
            "events_arbitrated": 0,
            "contributors_weighed": 0,
            "links_traced": 0,
            "moral_blame_assigned": 0,
            "negligent_blame_assigned": 0,
            "accidental_blame_assigned": 0,
            "verdicts_overturned": 0,
            "last_cycle_at": 0.0,
            "uptime_started_at": time.time(),
            "last_cycle_time_ms": 0.0,
            "vitality": ArbiterVitality.IDLE.value,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        """Update stats. Cumulative counters accumulate; others replace."""
        cumulative_keys = {
            "cycles_completed", "events_arbitrated", "contributors_weighed",
            "links_traced", "moral_blame_assigned", "negligent_blame_assigned",
            "accidental_blame_assigned", "verdicts_overturned",
        }
        for k, v in kwargs.items():
            if k in cumulative_keys and isinstance(v, (int, float)):
                self._stats[k] = self._stats.get(k, 0) + v
            else:
                self._stats[k] = v
        self._stats["vitality"] = self._derive_vitality().value

    def _derive_vitality(self) -> ArbiterVitality:
        pending = sum(
            1 for ev in self._events.values()
            if ev.get("state") != VerdictState.RECORDED.value
        )
        if pending == 0:
            return ArbiterVitality.IDLE
        if pending >= self._VITALITY_SATURATED_THRESHOLD:
            return ArbiterVitality.SATURATED
        if pending >= self._VITALITY_BACKLOGGED_THRESHOLD:
            return ArbiterVitality.BACKLOGGED
        if pending >= self._VITALITY_ACTIVE_THRESHOLD:
            return ArbiterVitality.ACTIVE
        return ArbiterVitality.DELIBERATING

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Event Intake
    # -------------------------------------------------------------------------

    def register_event(self, event_id: str,
                       contributors: Optional[List[Dict[str, Any]]] = None,
                       links: Optional[List[Dict[str, Any]]] = None,
                       note: str = "") -> Dict[str, Any]:
        """Register a narrative event with its candidate contributors and links."""
        with self._global_lock:
            if event_id in self._events:
                return {"error": f"Event already registered: {event_id}"}
            contributor_objs: List[Contributor] = []
            for c in (contributors or [])[:self._MAX_CONTRIBUTORS]:
                contributor_objs.append(Contributor(
                    contributor_id=c.get("contributor_id", ""),
                    role=c.get("role", ""),
                    intent_score=max(0.0, min(1.0, float(c.get("intent_score", 0.0)))),
                    foresight_score=max(0.0, min(1.0, float(c.get("foresight_score", 0.0)))),
                    negligence_score=max(0.0, min(1.0, float(c.get("negligence_score", 0.0)))),
                    proximate_strength=max(0.0, min(1.0, float(c.get("proximate_strength", 0.0)))),
                    note=c.get("note", ""),
                ))
            link_objs: List[CausalLink] = []
            for l in (links or [])[:self._MAX_CONTRIBUTORS]:
                strength_str = l.get("strength", "moderate")
                try:
                    strength = ChainLinkStrength(strength_str)
                except ValueError:
                    strength = ChainLinkStrength.MODERATE
                link_objs.append(CausalLink(
                    from_id=l.get("from_id", ""),
                    to_id=l.get("to_id", ""),
                    strength=strength,
                    note=l.get("note", ""),
                ))
            self._events[event_id] = {
                "event_id": event_id,
                "contributors": contributor_objs,
                "links": link_objs,
                "assignments": [],
                "state": VerdictState.PENDING.value,
                "note": note,
                "created_at": time.time(),
                "recorded_at": None,
                "gathered": False,
            }
            # Cap total events by dropping the oldest.
            if len(self._events) > self._MAX_EVENTS:
                oldest = min(
                    self._events,
                    key=lambda eid: self._events[eid].get("created_at", 0.0),
                )
                self._events.pop(oldest, None)
            self._record_event("event_registered", {
                "event_id": event_id,
                "contributors": len(contributor_objs),
                "links": len(link_objs),
            })
            return {
                "event_id": event_id,
                "contributors": len(contributor_objs),
                "links": len(link_objs),
                "state": VerdictState.PENDING.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single arbitration cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ArbiterPhase.GATHER
            phase_outputs.append(self._phase_gather())
            self._phase = ArbiterPhase.TRACE
            phase_outputs.append(self._phase_trace())
            self._phase = ArbiterPhase.WEIGH
            phase_outputs.append(self._phase_weigh())
            self._phase = ArbiterPhase.ARBITRATE
            phase_outputs.append(self._phase_arbitrate())
            self._phase = ArbiterPhase.RECORD
            phase_outputs.append(self._phase_record())
            self._cycle_count += 1
            self._update_stats(
                cycles_completed=1,
                last_cycle_at=time.time(),
            )
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_gather(self) -> Dict[str, Any]:
        """GATHER phase: collect pending events and validate their contributors."""
        gathered = 0
        contributors_collected = 0
        for event in self._events.values():
            if event["state"] != VerdictState.PENDING.value:
                continue
            # Cap contributors to the maximum.
            contributors = event["contributors"][:self._MAX_CONTRIBUTORS]
            event["contributors"] = contributors
            event["gathered"] = True
            gathered += 1
            contributors_collected += len(contributors)
        self._record_event("phase_gather", {
            "gathered": gathered,
            "contributors_collected": contributors_collected,
        })
        return {
            "phase": ArbiterPhase.GATHER.value,
            "gathered": gathered,
            "contributors_collected": contributors_collected,
        }

    def _phase_trace(self) -> Dict[str, Any]:
        """TRACE phase: build the causal chain backward, marking each link's strength."""
        traced = 0
        links_marked = 0
        for event in self._events.values():
            if event["state"] != VerdictState.PENDING.value:
                continue
            contributors = event["contributors"]
            links = list(event["links"])
            # If no links were provided, synthesize a chain from each
            # contributor to the event based on proximate strength.
            if not links:
                for c in contributors:
                    links.append(CausalLink(
                        from_id=c.contributor_id,
                        to_id=event["event_id"],
                        strength=self._strength_from_proximate(c.proximate_strength),
                        note=f"synthesized link from {c.contributor_id}",
                    ))
            else:
                # Refine each provided link's strength from its source contributor.
                for link in links:
                    src = next(
                        (c for c in contributors if c.contributor_id == link.from_id),
                        None,
                    )
                    if src is not None:
                        link.strength = self._strength_from_proximate(
                            max(src.proximate_strength, self._strength_value(link.strength))
                        )
            # Cap total links to keep the chain bounded.
            cap = self._MAX_CHAIN_DEPTH * self._MAX_CONTRIBUTORS
            event["links"] = links[:cap]
            event["state"] = VerdictState.TRACED.value
            traced += 1
            links_marked += len(event["links"])
        self._update_stats(links_traced=links_marked)
        self._record_event("phase_trace", {
            "traced": traced,
            "links_marked": links_marked,
        })
        return {
            "phase": ArbiterPhase.TRACE.value,
            "traced": traced,
            "links_marked": links_marked,
        }

    def _phase_weigh(self) -> Dict[str, Any]:
        """WEIGH phase: score each contributor on intent, foresight, negligence, proximate strength."""
        weighed = 0
        contributors_scored = 0
        for event in self._events.values():
            if event["state"] != VerdictState.TRACED.value:
                continue
            for c in event["contributors"]:
                # Add small deliberation noise to each dimension.
                c.intent_score = max(0.0, min(1.0, c.intent_score + random.uniform(-0.03, 0.03)))
                c.foresight_score = max(0.0, min(1.0, c.foresight_score + random.uniform(-0.03, 0.03)))
                c.negligence_score = max(0.0, min(1.0, c.negligence_score + random.uniform(-0.03, 0.03)))
                c.proximate_strength = max(0.0, min(1.0, c.proximate_strength + random.uniform(-0.03, 0.03)))
                # Store the raw blame score on the contributor for the next phase.
                setattr(c, "blame_score", self._raw_blame_score(c))
                contributors_scored += 1
            event["state"] = VerdictState.WEIGHED.value
            weighed += 1
        self._update_stats(contributors_weighed=contributors_scored)
        self._record_event("phase_weigh", {
            "weighed": weighed,
            "contributors_scored": contributors_scored,
        })
        return {
            "phase": ArbiterPhase.WEIGH.value,
            "weighed": weighed,
            "contributors_scored": contributors_scored,
        }

    def _phase_arbitrate(self) -> Dict[str, Any]:
        """ARBITRATE phase: convert weights into a blame assignment summing to 1.0."""
        arbitrated = 0
        moral_count = 0
        negligent_count = 0
        accidental_count = 0
        for event in self._events.values():
            if event["state"] != VerdictState.WEIGHED.value:
                continue
            contributors = event["contributors"]
            assignments: List[BlameAssignment] = []
            if contributors:
                total_score = sum(
                    getattr(c, "blame_score", 0.0) for c in contributors
                )
                if total_score <= 0.0:
                    # Everyone is blameless; distribute evenly as accidental.
                    even_share = 1.0 / len(contributors)
                    for c in contributors:
                        assignments.append(BlameAssignment(
                            contributor_id=c.contributor_id,
                            share=even_share,
                            flavor=BlameFlavor.ACCIDENTAL,
                            rationale="no contributor rose above zero blame; share is even",
                        ))
                        accidental_count += 1
                else:
                    for c in contributors:
                        share = getattr(c, "blame_score", 0.0) / total_score
                        flavor = self._classify_flavor(c)
                        rationale = self._compose_rationale(c, flavor, share)
                        assignments.append(BlameAssignment(
                            contributor_id=c.contributor_id,
                            share=share,
                            flavor=flavor,
                            rationale=rationale,
                        ))
                        if flavor == BlameFlavor.MORAL:
                            moral_count += 1
                        elif flavor == BlameFlavor.NEGLIGENT:
                            negligent_count += 1
                        elif flavor == BlameFlavor.ACCIDENTAL:
                            accidental_count += 1
            event["assignments"] = assignments
            event["state"] = VerdictState.ARBITRATED.value
            arbitrated += 1
        self._update_stats(
            events_arbitrated=arbitrated,
            moral_blame_assigned=moral_count,
            negligent_blame_assigned=negligent_count,
            accidental_blame_assigned=accidental_count,
        )
        self._record_event("phase_arbitrate", {
            "arbitrated": arbitrated,
            "moral": moral_count,
            "negligent": negligent_count,
            "accidental": accidental_count,
        })
        return {
            "phase": ArbiterPhase.ARBITRATE.value,
            "arbitrated": arbitrated,
            "moral": moral_count,
            "negligent": negligent_count,
            "accidental": accidental_count,
        }

    def _phase_record(self) -> Dict[str, Any]:
        """RECORD phase: write the assignment to the ledger and finalize the verdict."""
        recorded = 0
        for event in self._events.values():
            if event["state"] != VerdictState.ARBITRATED.value:
                continue
            assignment_dicts = [
                {
                    "contributor_id": a.contributor_id,
                    "share": a.share,
                    "flavor": a.flavor.value,
                    "rationale": a.rationale,
                }
                for a in event["assignments"]
            ]
            self._ledger[event["event_id"]] = assignment_dicts
            # Cap ledger size by dropping the oldest entry.
            if len(self._ledger) > self._MAX_LEDGER_ENTRIES:
                oldest = min(
                    self._ledger.keys(),
                    key=lambda eid: self._events.get(eid, {}).get("created_at", 0.0),
                )
                self._ledger.pop(oldest, None)
            event["state"] = VerdictState.RECORDED.value
            event["recorded_at"] = time.time()
            recorded += 1
        self._record_event("phase_record", {"recorded": recorded})
        return {
            "phase": ArbiterPhase.RECORD.value,
            "recorded": recorded,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _raw_blame_score(self, c: Contributor) -> float:
        """Compute a raw (pre-normalization) blame score for a contributor."""
        return (
            c.intent_score * self._DIMENSION_WEIGHTS[BlameDimension.INTENT]
            + c.foresight_score * self._DIMENSION_WEIGHTS[BlameDimension.FORESIGHT]
            + c.negligence_score * self._DIMENSION_WEIGHTS[BlameDimension.NEGLIGENCE]
            + c.proximate_strength * self._DIMENSION_WEIGHTS[BlameDimension.PROXIMATE_STRENGTH]
        )

    def _classify_flavor(self, c: Contributor) -> BlameFlavor:
        """Classify the flavor of blame a contributor deserves."""
        if c.intent_score >= self._MORAL_INTENT_THRESHOLD:
            return BlameFlavor.MORAL
        if c.negligence_score >= self._NEGLIGENT_THRESHOLD:
            return BlameFlavor.NEGLIGENT
        if c.intent_score <= self._ACCIDENTAL_THRESHOLD and c.negligence_score <= self._ACCIDENTAL_THRESHOLD:
            return BlameFlavor.ACCIDENTAL
        if c.proximate_strength >= self._CAUSAL_PROXIMATE_THRESHOLD:
            return BlameFlavor.CAUSAL
        return BlameFlavor.INHERENT

    def _compose_rationale(self, c: Contributor, flavor: BlameFlavor, share: float) -> str:
        """Compose a short rationale for a blame assignment."""
        flavor_text = {
            BlameFlavor.MORAL: "meant it",
            BlameFlavor.CAUSAL: "made it possible",
            BlameFlavor.NEGLIGENT: "should have seen it",
            BlameFlavor.INHERENT: "in their nature",
            BlameFlavor.ACCIDENTAL: "no one meant it",
        }
        return (
            f"{c.contributor_id} ({c.role}) bears {share:.2f} of the blame; "
            f"{flavor_text.get(flavor, flavor.value)}"
        )

    def _strength_from_proximate(self, proximate: float) -> ChainLinkStrength:
        """Map a proximate strength score to a chain link strength."""
        if proximate >= 0.8:
            return ChainLinkStrength.DIRECT
        if proximate >= 0.6:
            return ChainLinkStrength.STRONG
        if proximate >= 0.4:
            return ChainLinkStrength.MODERATE
        if proximate >= 0.2:
            return ChainLinkStrength.WEAK
        return ChainLinkStrength.TENUOUS

    def _strength_value(self, strength: ChainLinkStrength) -> float:
        """Convert a chain link strength to a numeric proximate value."""
        return {
            ChainLinkStrength.DIRECT: 0.9,
            ChainLinkStrength.STRONG: 0.7,
            ChainLinkStrength.MODERATE: 0.5,
            ChainLinkStrength.WEAK: 0.3,
            ChainLinkStrength.TENUOUS: 0.1,
        }.get(strength, 0.5)

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_verdict(self, event_id: str) -> Dict[str, Any]:
        with self._global_lock:
            event = self._events.get(event_id)
            if event is None:
                return {"error": f"Event not found: {event_id}"}
            return {
                "event_id": event_id,
                "state": event["state"],
                "note": event.get("note", ""),
                "created_at": event.get("created_at"),
                "recorded_at": event.get("recorded_at"),
                "contributors": [
                    {
                        "contributor_id": c.contributor_id,
                        "role": c.role,
                        "intent_score": c.intent_score,
                        "foresight_score": c.foresight_score,
                        "negligence_score": c.negligence_score,
                        "proximate_strength": c.proximate_strength,
                        "blame_score": getattr(c, "blame_score", 0.0),
                        "note": c.note,
                    }
                    for c in event["contributors"]
                ],
                "links": [
                    {
                        "from_id": l.from_id,
                        "to_id": l.to_id,
                        "strength": l.strength.value,
                        "note": l.note,
                    }
                    for l in event["links"]
                ],
                "assignments": [
                    {
                        "contributor_id": a.contributor_id,
                        "share": a.share,
                        "flavor": a.flavor.value,
                        "rationale": a.rationale,
                    }
                    for a in event["assignments"]
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "events": len(self._events),
                "ledger_entries": len(self._ledger),
                "stats": dict(self._stats),
            }

    def get_ledger(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "ledger": dict(self._ledger),
                "count": len(self._ledger),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic events and run multiple arbitration cycles."""
        with self._global_lock:
            self._seed_synthetic_events()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_events(self) -> None:
        """Seed a small synthetic set of narrative events with contributors."""
        seed_events = [
            ("sim_evt1", "the granary burned",
             [
                 {"contributor_id": "sim_arsonist", "role": "initiator",
                  "intent_score": 0.9, "foresight_score": 0.8,
                  "negligence_score": 0.1, "proximate_strength": 0.95,
                  "note": "struck the match"},
                 {"contributor_id": "sim_guard", "role": "watchman",
                  "intent_score": 0.0, "foresight_score": 0.4,
                  "negligence_score": 0.8, "proximate_strength": 0.3,
                  "note": "asleep on duty"},
                 {"contributor_id": "sim_quartermaster", "role": "supplier",
                  "intent_score": 0.1, "foresight_score": 0.3,
                  "negligence_score": 0.5, "proximate_strength": 0.4,
                  "note": "stored the grain dry"},
             ],
             [
                 {"from_id": "sim_arsonist", "to_id": "sim_evt1", "strength": "direct"},
                 {"from_id": "sim_guard", "to_id": "sim_evt1", "strength": "weak"},
             ]),
            ("sim_evt2", "the treaty collapsed",
             [
                 {"contributor_id": "sim_envoy", "role": "negotiator",
                  "intent_score": 0.3, "foresight_score": 0.7,
                  "negligence_score": 0.6, "proximate_strength": 0.6,
                  "note": "walked out of talks"},
                 {"contributor_id": "sim_monarch", "role": "principal",
                  "intent_score": 0.5, "foresight_score": 0.5,
                  "negligence_score": 0.3, "proximate_strength": 0.5,
                  "note": "set the envoy's mandate"},
             ],
             []),
            ("sim_evt3", "the child wandered into the woods",
             [
                 {"contributor_id": "sim_parent", "role": "guardian",
                  "intent_score": 0.0, "foresight_score": 0.2,
                  "negligence_score": 0.7, "proximate_strength": 0.4,
                  "note": "left the gate open"},
                 {"contributor_id": "sim_child", "role": "wanderer",
                  "intent_score": 0.1, "foresight_score": 0.05,
                  "negligence_score": 0.05, "proximate_strength": 0.6,
                  "note": "chased a firefly"},
             ],
             []),
        ]
        for event_id, note, contributors, links in seed_events:
            if event_id in self._events:
                continue
            self.register_event(
                event_id, contributors=contributors, links=links, note=note,
            )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._events.clear()
            self._ledger.clear()
            self._events_log.clear()
            self._phase = ArbiterPhase.GATHER
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
