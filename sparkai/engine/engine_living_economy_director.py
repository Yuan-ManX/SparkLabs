"""
SparkLabs Engine - Living Economy Director"""

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

class EconomyPhase(Enum):
    """Phases of the living economy cycle."""
    PRODUCE = "produce"            # producers make goods from their inputs
    EXCHANGE = "exchange"          # goods flow between buyers and sellers
    VALUATE = "valuate"            # every good is revalued against supply and demand
    REDISTRIBUTE = "redistribute"  # flow is rerouted where the system is starving or choking
    EQUILIBRATE = "equilibrate"    # the whole ecosystem is nudged toward balance


class GoodKind(Enum):
    """The kind of good flowing through the economy."""
    STAPLE = "staple"              # food, water, basics
    LUXURY = "luxury"              # finery, comforts
    MATERIAL = "material"          # wood, ore, cloth
    TOOL = "tool"                  # things that make other things
    CURIOSITY = "curiosity"        # strange things of uncertain worth


class ProducerArchetype(Enum):
    """The archetype of a producer in the economy."""
    GROWER = "grower"              # turns land and labor into staples
    ARTISAN = "artisan"            # turns materials and tools into luxuries
    MINER = "miner"                # turns land and tools into materials
    SMITH = "smith"                # turns materials and tools into tools
    SCAVENGER = "scavenger"        # turns curiosity into anything


class ExchangeRole(Enum):
    """The role a participant plays in an exchange."""
    BUYER = "buyer"
    SELLER = "seller"
    BROKER = "broker"              # facilitates buyer and seller


class FlowState(Enum):
    """State of an individual flow of goods."""
    PRODUCED = "produced"          # goods have been made
    EXCHANGED = "exchanged"        # goods have moved between participants
    VALUATED = "valuated"          # goods have been repriced
    REDISTRIBUTED = "redistributed"  # flow has been rerouted
    EQUILIBRATED = "equilibrated"  # flow has settled toward balance


class EconomyHealth(Enum):
    """The overall health of the living economy."""
    STARVING = "starving"          # too little production
    CONSTIPATED = "constipated"    # production but no exchange
    VOLATILE = "volatile"          # prices swing wildly
    BALANCED = "balanced"          # production, exchange, and prices agree
    GLUTTED = "glutted"            # too much production, prices collapsing


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Good:
    """A kind of good tracked by the economy."""
    good_id: str
    kind: GoodKind
    supply: float = 0.0           # current stock in the ecosystem
    demand: float = 0.0           # current want in the ecosystem
    price: float = 0.5            # 0.0-1.0, normalized price
    volatility: float = 0.2       # 0.0-1.0, how much the price swings


@dataclass
class Producer:
    """A producer that turns inputs into a good."""
    producer_id: str
    archetype: ProducerArchetype
    output_good_id: str
    input_good_ids: List[str] = field(default_factory=list)
    productivity: float = 0.5     # 0.0-1.0, how much it produces per cycle
    stockpile: float = 0.0        # goods waiting to be exchanged
    total_produced: float = 0.0


@dataclass
class Exchange:
    """A single exchange of goods between participants."""
    exchange_id: str
    good_id: str
    buyer_id: str
    seller_id: str
    quantity: float = 0.0
    price: float = 0.5
    broker_id: str = ""
    state: FlowState = FlowState.PRODUCED
    created_at: float = field(default_factory=time.time)


@dataclass
class EconomyParticipant:
    """A participant in the economy (producer, buyer, seller, broker)."""
    participant_id: str
    role: ExchangeRole
    needs: Dict[str, float] = field(default_factory=dict)   # good_id -> want level
    surpluses: Dict[str, float] = field(default_factory=dict)  # good_id -> surplus level
    liquidity: float = 0.5       # 0.0-1.0, how readily it can transact


@dataclass
class EconomyState:
    """Aggregate state of the living economy."""
    total_produced: float = 0.0
    total_exchanged: float = 0.0
    price_index: float = 0.5      # average price across goods
    supply_demand_ratio: float = 1.0
    flow_velocity: float = 0.0    # how fast goods are moving
    health: EconomyHealth = EconomyHealth.BALANCED
    signature: str = ""


# =============================================================================
# Director
# =============================================================================

class EngineLivingEconomyDirector:
    """
    Thread-safe singleton orchestrating the living economy.

    Usage:
        director = EngineLivingEconomyDirector.get_instance()
        director.register_good("grain", GoodKind.STAPLE)
        director.register_producer("farm1", ProducerArchetype.GROWER,
                                   output_good_id="grain",
                                   input_good_ids=[], productivity=0.6)
        director.register_participant("merchant", ExchangeRole.BROKER)
        director.cycle()
        state = director.get_status()
    """

    _instance: Optional["EngineLivingEconomyDirector"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _PRODUCE_BASE = 0.3                  # base production per cycle
    _EXCHANGE_MATCH_THRESHOLD = 0.2      # surplus-need overlap needed to exchange
    _VALUATE_PRICE_ADJUSTMENT = 0.15     # how fast prices move toward equilibrium
    _REDISTRIBUTE_STARVATION_THRESHOLD = 0.2  # supply below this is starving
    _REDISTRIBUTE_GLUT_THRESHOLD = 0.8   # supply above this is a glut
    _EQUILIBRATE_NUDGE = 0.1             # how hard the system nudges toward balance
    _MAX_GOODS = 50
    _MAX_PRODUCERS = 80
    _MAX_PARTICIPANTS = 80
    _MAX_EXCHANGES = 200
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._goods: Dict[str, Good] = {}
        self._producers: Dict[str, Producer] = {}
        self._participants: Dict[str, EconomyParticipant] = {}
        self._exchanges: Deque[Exchange] = deque(maxlen=self._MAX_EXCHANGES)
        self._state: EconomyState = EconomyState()
        self._phase: EconomyPhase = EconomyPhase.PRODUCE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineLivingEconomyDirector":
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
            "total_goods": 0,
            "total_producers": 0,
            "total_participants": 0,
            "total_produced": 0.0,
            "total_exchanged": 0.0,
            "price_index": 0.5,
            "supply_demand_ratio": 1.0,
            "flow_velocity": 0.0,
            "health": EconomyHealth.BALANCED.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        self._stats["total_goods"] = len(self._goods)
        self._stats["total_producers"] = len(self._producers)
        self._stats["total_participants"] = len(self._participants)
        self._stats["total_produced"] = self._state.total_produced
        self._stats["total_exchanged"] = self._state.total_exchanged
        self._stats["price_index"] = self._state.price_index
        self._stats["supply_demand_ratio"] = self._state.supply_demand_ratio
        self._stats["flow_velocity"] = self._state.flow_velocity
        self._stats["health"] = self._state.health.value

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register_good(self, good_id: str, kind: GoodKind,
                      initial_supply: float = 0.3,
                      initial_demand: float = 0.3) -> Dict[str, Any]:
        """Register a new good in the economy."""
        with self._global_lock:
            if good_id in self._goods:
                return {"error": f"Good already registered: {good_id}"}
            if len(self._goods) >= self._MAX_GOODS:
                return {"error": f"Good cap reached ({self._MAX_GOODS})"}
            good = Good(
                good_id=good_id,
                kind=kind,
                supply=max(0.0, min(1.0, initial_supply)),
                demand=max(0.0, min(1.0, initial_demand)),
            )
            self._goods[good_id] = good
            self._record_event("good_registered", {
                "good_id": good_id, "kind": kind.value,
            })
            return {
                "good_id": good_id,
                "kind": kind.value,
                "supply": good.supply,
                "demand": good.demand,
                "price": good.price,
            }

    def register_producer(self, producer_id: str, archetype: ProducerArchetype,
                          output_good_id: str, input_good_ids: Optional[List[str]] = None,
                          productivity: float = 0.5) -> Dict[str, Any]:
        """Register a new producer in the economy."""
        with self._global_lock:
            if producer_id in self._producers:
                return {"error": f"Producer already registered: {producer_id}"}
            if len(self._producers) >= self._MAX_PRODUCERS:
                return {"error": f"Producer cap reached ({self._MAX_PRODUCERS})"}
            if output_good_id not in self._goods:
                return {"error": f"Output good not found: {output_good_id}"}
            producer = Producer(
                producer_id=producer_id,
                archetype=archetype,
                output_good_id=output_good_id,
                input_good_ids=input_good_ids or [],
                productivity=max(0.0, min(1.0, productivity)),
            )
            self._producers[producer_id] = producer
            self._record_event("producer_registered", {
                "producer_id": producer_id,
                "archetype": archetype.value,
                "output_good_id": output_good_id,
            })
            return {
                "producer_id": producer_id,
                "archetype": archetype.value,
                "output_good_id": output_good_id,
                "productivity": producer.productivity,
            }

    def register_participant(self, participant_id: str, role: ExchangeRole,
                             liquidity: float = 0.5) -> Dict[str, Any]:
        """Register a new participant in the economy."""
        with self._global_lock:
            if participant_id in self._participants:
                return {"error": f"Participant already registered: {participant_id}"}
            if len(self._participants) >= self._MAX_PARTICIPANTS:
                return {"error": f"Participant cap reached ({self._MAX_PARTICIPANTS})"}
            participant = EconomyParticipant(
                participant_id=participant_id,
                role=role,
                liquidity=max(0.0, min(1.0, liquidity)),
            )
            self._participants[participant_id] = participant
            self._record_event("participant_registered", {
                "participant_id": participant_id,
                "role": role.value,
            })
            return {
                "participant_id": participant_id,
                "role": role.value,
                "liquidity": participant.liquidity,
            }

    def set_participant_need(self, participant_id: str, good_id: str,
                             level: float) -> Dict[str, Any]:
        """Set a participant's need level for a good."""
        with self._global_lock:
            participant = self._participants.get(participant_id)
            if participant is None:
                return {"error": f"Participant not found: {participant_id}"}
            if good_id not in self._goods:
                return {"error": f"Good not found: {good_id}"}
            participant.needs[good_id] = max(0.0, min(1.0, level))
            return {
                "participant_id": participant_id,
                "good_id": good_id,
                "need": participant.needs[good_id],
            }

    def set_participant_surplus(self, participant_id: str, good_id: str,
                                level: float) -> Dict[str, Any]:
        """Set a participant's surplus level for a good."""
        with self._global_lock:
            participant = self._participants.get(participant_id)
            if participant is None:
                return {"error": f"Participant not found: {participant_id}"}
            if good_id not in self._goods:
                return {"error": f"Good not found: {good_id}"}
            participant.surpluses[good_id] = max(0.0, min(1.0, level))
            return {
                "participant_id": participant_id,
                "good_id": good_id,
                "surplus": participant.surpluses[good_id],
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single living economy cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = EconomyPhase.PRODUCE
            phase_outputs["produce"] = self._phase_produce()
            self._phase = EconomyPhase.EXCHANGE
            phase_outputs["exchange"] = self._phase_exchange()
            self._phase = EconomyPhase.VALUATE
            phase_outputs["valuate"] = self._phase_valuate()
            self._phase = EconomyPhase.REDISTRIBUTE
            phase_outputs["redistribute"] = self._phase_redistribute()
            self._phase = EconomyPhase.EQUILIBRATE
            phase_outputs["equilibrate"] = self._phase_equilibrate()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_produce(self) -> Dict[str, Any]:
        """Produce phase: producers make goods from their inputs."""
        produced_total = 0.0
        produced_count = 0
        for producer in self._producers.values():
            good = self._goods.get(producer.output_good_id)
            if good is None:
                continue
            # Check that required inputs are available.
            inputs_available = True
            for input_id in producer.input_good_ids:
                input_good = self._goods.get(input_id)
                if input_good is None or input_good.supply < 0.1:
                    inputs_available = False
                    break
            if not inputs_available:
                continue
            # Produce based on productivity.
            amount = self._PRODUCE_BASE * producer.productivity
            # Consume inputs.
            for input_id in producer.input_good_ids:
                input_good = self._goods.get(input_id)
                if input_good is not None:
                    input_good.supply = max(0.0, input_good.supply - amount * 0.2)
            # Add to output good supply and producer stockpile.
            good.supply = min(1.0, good.supply + amount)
            producer.stockpile = min(1.0, producer.stockpile + amount)
            producer.total_produced += amount
            produced_total += amount
            produced_count += 1
        self._state.total_produced += produced_total
        self._record_event("phase_produce", {
            "produced_count": produced_count,
            "produced_total": produced_total,
        })
        return {"produced_count": produced_count, "produced_total": produced_total}

    def _phase_exchange(self) -> Dict[str, Any]:
        """Exchange phase: goods flow between buyers and sellers."""
        exchanged_total = 0.0
        exchanges_added = 0
        # Build maps of who needs what and who has surplus of what.
        sellers_by_good: Dict[str, List[str]] = {}
        buyers_by_good: Dict[str, List[str]] = {}
        brokers = []
        for participant in self._participants.values():
            for good_id, surplus in participant.surpluses.items():
                if surplus > self._EXCHANGE_MATCH_THRESHOLD:
                    sellers_by_good.setdefault(good_id, []).append(participant.participant_id)
            for good_id, need in participant.needs.items():
                if need > self._EXCHANGE_MATCH_THRESHOLD:
                    buyers_by_good.setdefault(good_id, []).append(participant.participant_id)
            if participant.role == ExchangeRole.BROKER:
                brokers.append(participant.participant_id)
        # Also let producers sell from their stockpiles.
        for producer in self._producers.values():
            if producer.stockpile > self._EXCHANGE_MATCH_THRESHOLD:
                sellers_by_good.setdefault(producer.output_good_id, []).append(
                    producer.producer_id
                )
        # Match buyers to sellers for each good.
        for good_id, seller_ids in sellers_by_good.items():
            good = self._goods.get(good_id)
            if good is None:
                continue
            buyer_ids = buyers_by_good.get(good_id, [])
            random.shuffle(seller_ids)
            random.shuffle(buyer_ids)
            for i in range(min(len(seller_ids), len(buyer_ids))):
                seller_id = seller_ids[i]
                buyer_id = buyer_ids[i]
                broker_id = brokers[i % len(brokers)] if brokers else ""
                quantity = self._EXCHANGE_MATCH_THRESHOLD
                # Pull from seller's surplus or producer stockpile.
                seller = self._participants.get(seller_id)
                producer = self._producers.get(seller_id)
                if seller is not None:
                    seller.surpluses[good_id] = max(0.0, seller.surpluses[good_id] - quantity)
                    seller.liquidity = min(1.0, seller.liquidity + 0.02)
                elif producer is not None:
                    producer.stockpile = max(0.0, producer.stockpile - quantity)
                # Push to buyer's need.
                buyer = self._participants.get(buyer_id)
                if buyer is not None:
                    buyer.needs[good_id] = max(0.0, buyer.needs[good_id] - quantity)
                    buyer.liquidity = min(1.0, buyer.liquidity + 0.02)
                # Reduce supply (goods are consumed by the buyer).
                good.supply = max(0.0, good.supply - quantity * 0.5)
                exchange = Exchange(
                    exchange_id=f"ex_{good_id}_{self._cycle_count}_{exchanges_added}",
                    good_id=good_id,
                    buyer_id=buyer_id,
                    seller_id=seller_id,
                    quantity=quantity,
                    price=good.price,
                    broker_id=broker_id,
                    state=FlowState.EXCHANGED,
                )
                self._exchanges.append(exchange)
                exchanges_added += 1
                exchanged_total += quantity
        self._state.total_exchanged += exchanged_total
        self._record_event("phase_exchange", {
            "exchanges_added": exchanges_added,
            "exchanged_total": exchanged_total,
        })
        return {"exchanges_added": exchanges_added, "exchanged_total": exchanged_total}

    def _phase_valuate(self) -> Dict[str, Any]:
        """Valuate phase: every good is revalued against current supply and demand."""
        valuated = 0
        price_moves: List[float] = []
        for good in self._goods.values():
            # Target price rises with demand and falls with supply.
            target = 0.5 + (good.demand - good.supply) * 0.5
            target = max(0.05, min(0.95, target))
            old_price = good.price
            good.price = old_price * (1 - self._VALUATE_PRICE_ADJUSTMENT) + \
                         target * self._VALUATE_PRICE_ADJUSTMENT
            good.volatility = max(0.0, min(1.0, abs(good.price - old_price) * 4 + good.volatility * 0.8))
            price_moves.append(abs(good.price - old_price))
            valuated += 1
        # Aggregate the price index across goods.
        if self._goods:
            self._state.price_index = sum(g.price for g in self._goods.values()) / len(self._goods)
        self._record_event("phase_valuate", {
            "valuated": valuated,
            "price_index": self._state.price_index,
        })
        return {"valuated": valuated, "price_index": self._state.price_index}

    def _phase_redistribute(self) -> Dict[str, Any]:
        """Redistribute phase: flow is rerouted where the system is starving or choking."""
        redistributed = 0
        for good in self._goods.values():
            if good.supply < self._REDISTRIBUTE_STARVATION_THRESHOLD:
                # Starving: bump demand down a little and encourage production by raising price.
                good.demand = max(0.0, good.demand - self._EQUILIBRATE_NUDGE * 0.5)
                good.price = min(1.0, good.price + self._EQUILIBRATE_NUDGE)
                redistributed += 1
            elif good.supply > self._REDISTRIBUTE_GLUT_THRESHOLD:
                # Glut: bump demand up a little and discourage production by lowering price.
                good.demand = min(1.0, good.demand + self._EQUILIBRATE_NUDGE * 0.5)
                good.price = max(0.0, good.price - self._EQUILIBRATE_NUDGE)
                redistributed += 1
        # Move surplus from glutted goods to producers of starving goods where possible.
        for producer in self._producers.values():
            output_good = self._goods.get(producer.output_good_id)
            if output_good is None:
                continue
            if output_good.supply < self._REDISTRIBUTE_STARVATION_THRESHOLD:
                # Encourage this producer to produce more next cycle.
                producer.productivity = min(1.0, producer.productivity + self._EQUILIBRATE_NUDGE * 0.5)
            elif output_good.supply > self._REDISTRIBUTE_GLUT_THRESHOLD:
                producer.productivity = max(0.0, producer.productivity - self._EQUILIBRATE_NUDGE * 0.5)
        self._record_event("phase_redistribute", {"redistributed": redistributed})
        return {"redistributed": redistributed}

    def _phase_equilibrate(self) -> Dict[str, Any]:
        """Equilibrate phase: the whole ecosystem is nudged toward balance."""
        equilibrated = 0
        total_supply = 0.0
        total_demand = 0.0
        for good in self._goods.values():
            # Nudge supply and demand gently toward each other.
            midpoint = (good.supply + good.demand) / 2.0
            good.supply = good.supply * (1 - self._EQUILIBRATE_NUDGE) + \
                          midpoint * self._EQUILIBRATE_NUDGE
            good.demand = good.demand * (1 - self._EQUILIBRATE_NUDGE) + \
                          midpoint * self._EQUILIBRATE_NUDGE
            total_supply += good.supply
            total_demand += good.demand
            equilibrated += 1
        # Compute supply-demand ratio and flow velocity.
        self._state.supply_demand_ratio = (
            total_supply / total_demand if total_demand > 0 else 1.0
        )
        recent_exchanges = list(self._exchanges)[-20:]
        self._state.flow_velocity = (
            sum(e.quantity for e in recent_exchanges) / 20.0 if recent_exchanges else 0.0
        )
        # Derive overall health.
        self._state.health = self._derive_health()
        self._state.signature = self._derive_signature()
        self._record_event("phase_equilibrate", {
            "equilibrated": equilibrated,
            "health": self._state.health.value,
        })
        return {
            "equilibrated": equilibrated,
            "health": self._state.health.value,
            "supply_demand_ratio": self._state.supply_demand_ratio,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _derive_health(self) -> EconomyHealth:
        """Derive the overall health of the economy."""
        if not self._goods:
            return EconomyHealth.BALANCED
        # Average volatility across goods.
        avg_volatility = sum(g.volatility for g in self._goods.values()) / len(self._goods)
        ratio = self._state.supply_demand_ratio
        if self._state.total_produced < 0.1 and self._state.total_exchanged < 0.1:
            return EconomyHealth.STARVING
        if self._state.total_produced > 0.1 and self._state.total_exchanged < 0.05:
            return EconomyHealth.CONSTIPATED
        if avg_volatility > 0.5:
            return EconomyHealth.VOLATILE
        if ratio > 1.8:
            return EconomyHealth.GLUTTED
        return EconomyHealth.BALANCED

    def _derive_signature(self) -> str:
        """Derive a signature phrase for the economy."""
        health = self._state.health
        if not self._goods:
            return "empty economy"
        ratio = self._state.supply_demand_ratio
        if ratio > 1.5:
            flow = "fat"
        elif ratio < 0.7:
            flow = "lean"
        else:
            flow = "even"
        return f"{flow} {health.value} economy"

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_good(self, good_id: str) -> Dict[str, Any]:
        with self._global_lock:
            good = self._goods.get(good_id)
            if good is None:
                return {"error": f"Good not found: {good_id}"}
            return {
                "good_id": good.good_id,
                "kind": good.kind.value,
                "supply": good.supply,
                "demand": good.demand,
                "price": good.price,
                "volatility": good.volatility,
            }

    def get_goods(self, limit: int = 30) -> Dict[str, Any]:
        with self._global_lock:
            goods = list(self._goods.values())[:limit]
            return {
                "goods": [
                    {
                        "good_id": g.good_id,
                        "kind": g.kind.value,
                        "supply": g.supply,
                        "demand": g.demand,
                        "price": g.price,
                    }
                    for g in goods
                ],
            }

    def get_producer(self, producer_id: str) -> Dict[str, Any]:
        with self._global_lock:
            producer = self._producers.get(producer_id)
            if producer is None:
                return {"error": f"Producer not found: {producer_id}"}
            return {
                "producer_id": producer.producer_id,
                "archetype": producer.archetype.value,
                "output_good_id": producer.output_good_id,
                "input_good_ids": producer.input_good_ids,
                "productivity": producer.productivity,
                "stockpile": producer.stockpile,
                "total_produced": producer.total_produced,
            }

    def get_participant(self, participant_id: str) -> Dict[str, Any]:
        with self._global_lock:
            participant = self._participants.get(participant_id)
            if participant is None:
                return {"error": f"Participant not found: {participant_id}"}
            return {
                "participant_id": participant.participant_id,
                "role": participant.role.value,
                "needs": dict(participant.needs),
                "surpluses": dict(participant.surpluses),
                "liquidity": participant.liquidity,
            }

    def get_exchanges(self, limit: int = 30) -> Dict[str, Any]:
        with self._global_lock:
            exchanges = list(self._exchanges)[-limit:]
            return {
                "exchanges": [
                    {
                        "exchange_id": e.exchange_id,
                        "good_id": e.good_id,
                        "buyer_id": e.buyer_id,
                        "seller_id": e.seller_id,
                        "broker_id": e.broker_id,
                        "quantity": e.quantity,
                        "price": e.price,
                        "state": e.state.value,
                    }
                    for e in exchanges
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "goods": len(self._goods),
                "producers": len(self._producers),
                "participants": len(self._participants),
                "state": {
                    "total_produced": self._state.total_produced,
                    "total_exchanged": self._state.total_exchanged,
                    "price_index": self._state.price_index,
                    "supply_demand_ratio": self._state.supply_demand_ratio,
                    "flow_velocity": self._state.flow_velocity,
                    "health": self._state.health.value,
                    "signature": self._state.signature,
                },
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic goods, producers, and participants, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_economy()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_economy(self) -> None:
        """Seed a small synthetic economy with goods, producers, and participants."""
        seed_goods = [
            ("sim_grain", GoodKind.STAPLE, 0.4, 0.5),
            ("sim_ore", GoodKind.MATERIAL, 0.4, 0.4),
            ("sim_tools", GoodKind.TOOL, 0.3, 0.5),
            ("sim_finery", GoodKind.LUXURY, 0.2, 0.4),
            ("sim_curio", GoodKind.CURIOSITY, 0.1, 0.2),
        ]
        for good_id, kind, supply, demand in seed_goods:
            if good_id not in self._goods:
                self.register_good(good_id, kind, initial_supply=supply, initial_demand=demand)
        seed_producers = [
            ("sim_farm", ProducerArchetype.GROWER, "sim_grain", [], 0.6),
            ("sim_mine", ProducerArchetype.MINER, "sim_ore", ["sim_tools"], 0.5),
            ("sim_smith", ProducerArchetype.SMITH, "sim_tools", ["sim_ore"], 0.5),
            ("sim_artisan", ProducerArchetype.ARTISAN, "sim_finery", ["sim_ore", "sim_tools"], 0.4),
            ("sim_scavenger", ProducerArchetype.SCAVENGER, "sim_curio", [], 0.3),
        ]
        for producer_id, archetype, output_id, input_ids, productivity in seed_producers:
            if producer_id not in self._producers:
                self.register_producer(producer_id, archetype, output_id,
                                       input_good_ids=input_ids, productivity=productivity)
        seed_participants = [
            ("sim_merchant", ExchangeRole.BROKER, 0.7),
            ("sim_quarter", ExchangeRole.BUYER, 0.5),
            ("sim_trader", ExchangeRole.SELLER, 0.6),
        ]
        for participant_id, role, liquidity in seed_participants:
            if participant_id not in self._participants:
                self.register_participant(participant_id, role, liquidity=liquidity)
        # Wire up needs and surpluses.
        if "sim_quarter" in self._participants:
            self.set_participant_need("sim_quarter", "sim_grain", 0.6)
            self.set_participant_need("sim_quarter", "sim_tools", 0.5)
        if "sim_trader" in self._participants:
            self.set_participant_surplus("sim_trader", "sim_finery", 0.5)
            self.set_participant_surplus("sim_trader", "sim_curio", 0.4)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._goods.clear()
            self._producers.clear()
            self._participants.clear()
            self._exchanges.clear()
            self._state = EconomyState()
            self._phase = EconomyPhase.PRODUCE
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}
