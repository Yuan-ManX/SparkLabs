"""
SparkLabs Agent - Game Economy Simulator

Simulates in-game economic systems for AI-native game development.
Models resource flows, market dynamics, inflation, and trader behavior
across different economic model types. Provides stress testing and
comprehensive economic health reporting.

Architecture:
  EconomySimulator
    |-- EconomyConfig (economy-wide parameters and model selection)
    |-- ResourceDef (tradable resource definitions with supply/demand curves)
    |-- MarketTransaction (individual trade records with price tracking)
    |-- EconomySnapshot (per-tick economic state capture)
    |-- InflationDetector (price trend analysis and severity classification)
    |-- StressTestEngine (extreme scenario simulation)

Economic Models:
  FREE_MARKET - prices driven by supply and demand
  COMMAND - centrally controlled fixed pricing
  GIFT - resources distributed without currency exchange
  MIXED - hybrid model with regulated free market
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EconomyModel(Enum):
    FREE_MARKET = "free_market"
    COMMAND = "command"
    GIFT = "gift"
    MIXED = "mixed"


class CurrencyType(Enum):
    SOFT = "soft"
    HARD = "hard"
    PREMIUM = "premium"


class ResourceFlow(Enum):
    PRODUCTION = "production"
    CONSUMPTION = "consumption"
    TRADE = "trade"
    DESTRUCTION = "destruction"


class MarketCondition(Enum):
    STABLE = "stable"
    INFLATIONARY = "inflationary"
    DEFLATIONARY = "deflationary"
    VOLATILE = "volatile"


@dataclass
class EconomyConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "default_economy"
    model: EconomyModel = EconomyModel.FREE_MARKET
    initial_balance: float = 1000.0
    inflation_rate: float = 0.02
    max_inflation: float = 0.15
    currency_type: CurrencyType = CurrencyType.SOFT
    price_volatility: float = 0.05
    transaction_tax: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model.value,
            "initial_balance": self.initial_balance,
            "inflation_rate": self.inflation_rate,
            "max_inflation": self.max_inflation,
            "currency_type": self.currency_type.value,
            "price_volatility": self.price_volatility,
            "transaction_tax": self.transaction_tax,
        }


@dataclass
class ResourceDef:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    base_price: float = 10.0
    scarcity: float = 0.5
    production_rate: float = 1.0
    consumption_rate: float = 0.8
    category: str = "general"
    current_supply: float = 100.0
    current_demand: float = 80.0
    price_elasticity: float = 1.0
    min_price: float = 1.0
    max_price: float = 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_price": self.base_price,
            "scarcity": self.scarcity,
            "production_rate": self.production_rate,
            "consumption_rate": self.consumption_rate,
            "category": self.category,
            "current_supply": self.current_supply,
            "current_demand": self.current_demand,
        }


@dataclass
class MarketTransaction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    resource_id: str = ""
    amount: float = 1.0
    price: float = 0.0
    buyer: str = ""
    seller: str = ""
    timestamp: float = field(default_factory=time.time)
    flow_type: ResourceFlow = ResourceFlow.TRADE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "amount": self.amount,
            "price": self.price,
            "buyer": self.buyer,
            "seller": self.seller,
            "timestamp": self.timestamp,
            "flow_type": self.flow_type.value,
        }


@dataclass
class EconomySnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tick: int = 0
    total_money_supply: float = 0.0
    avg_price_index: float = 100.0
    gini_coefficient: float = 0.0
    active_traders: int = 0
    condition: MarketCondition = MarketCondition.STABLE
    timestamp: float = field(default_factory=time.time)
    resource_prices: Dict[str, float] = field(default_factory=dict)
    trader_balances: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tick": self.tick,
            "total_money_supply": self.total_money_supply,
            "avg_price_index": self.avg_price_index,
            "gini_coefficient": self.gini_coefficient,
            "active_traders": self.active_traders,
            "condition": self.condition.value,
        }


class EconomySimulator:
    """
    Self-contained game economy simulation engine.

    Simulates in-game economic behavior including resource pricing,
    supply/demand dynamics, trader participation, and inflation.
    Supports multiple economic models and provides stress testing
    for extreme market conditions. All computations are simulated
    with no external API dependencies.
    """

    _instance: Optional["EconomySimulator"] = None

    def __init__(self):
        self._config: Optional[EconomyConfig] = None
        self._resources: Dict[str, ResourceDef] = {}
        self._traders: Dict[str, float] = {}
        self._transactions: List[MarketTransaction] = []
        self._snapshots: List[EconomySnapshot] = []
        self._tick: int = 0
        self._price_index: float = 100.0
        self._money_supply: float = 0.0
        self._lock = threading.Lock()
        self._MAX_TRANSACTIONS = 10000
        self._MAX_SNAPSHOTS = 500

    @classmethod
    def get_instance(cls) -> "EconomySimulator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_economy(self, config: EconomyConfig) -> EconomyConfig:
        with self._lock:
            self._config = config
            self._resources = {}
            self._traders = {}
            self._transactions = []
            self._snapshots = []
            self._tick = 0
            self._price_index = 100.0
            self._money_supply = 0.0
            return self._config

    def define_resource(self, resource_def: ResourceDef) -> str:
        with self._lock:
            self._resources[resource_def.id] = resource_def
            return resource_def.id

    def register_trader(self, trader_id: str, initial_balance: float) -> str:
        with self._lock:
            if self._config is not None:
                balance = initial_balance if initial_balance > 0 else self._config.initial_balance
            else:
                balance = initial_balance
            self._traders[trader_id] = balance
            self._money_supply += balance
            return trader_id

    def simulate_tick(self) -> EconomySnapshot:
        with self._lock:
            return self._simulate_tick_locked()

    def _simulate_tick_locked(self) -> EconomySnapshot:
        self._tick += 1

        if self._config is None:
            self._config = EconomyConfig()

        self._update_resource_supply_demand()
        self._process_trader_activity()
        self._adjust_prices()
        self._update_money_supply()

        condition = self._classify_market_condition()
        gini = self._compute_gini()

        resource_prices = {
            rid: self._compute_current_price(res)
            for rid, res in self._resources.items()
        }

        snapshot = EconomySnapshot(
            tick=self._tick,
            total_money_supply=self._money_supply,
            avg_price_index=round(self._price_index, 2),
            gini_coefficient=round(gini, 4),
            active_traders=len([b for b in self._traders.values() if b > 0]),
            condition=condition,
            resource_prices=resource_prices,
            trader_balances=dict(self._traders),
        )

        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._MAX_SNAPSHOTS:
            self._snapshots = self._snapshots[-self._MAX_SNAPSHOTS:]

        return snapshot

    def get_market_price(self, resource_id: str) -> Optional[float]:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            return round(self._compute_current_price(resource), 2)

    def detect_inflation(self) -> Dict[str, Any]:
        with self._lock:
            return self._detect_inflation_locked()

    def _detect_inflation_locked(self) -> Dict[str, Any]:
        if not self._snapshots or self._config is None:
            return {
                "detected": False,
                "severity": "none",
                "inflation_rate": 0.0,
                "price_index": self._price_index,
                "recommendation": "insufficient data for inflation analysis",
            }

        relevant = self._snapshots[-min(20, len(self._snapshots)):]
        if len(relevant) < 2:
            return {
                "detected": False,
                "severity": "none",
                "inflation_rate": 0.0,
                "price_index": self._price_index,
                "recommendation": "need more tick data for analysis",
            }

        start_price = relevant[0].avg_price_index
        end_price = relevant[-1].avg_price_index

        if start_price > 0:
            observed_inflation = (end_price - start_price) / start_price
        else:
            observed_inflation = 0.0

        severity = "none"
        if observed_inflation > self._config.max_inflation:
            severity = "critical"
        elif observed_inflation > self._config.max_inflation * 0.7:
            severity = "high"
        elif observed_inflation > self._config.inflation_rate * 2:
            severity = "moderate"
        elif observed_inflation > self._config.inflation_rate:
            severity = "low"

        recommendations = {
            "none": "economy is stable, no action needed",
            "low": "monitor price trends, consider minor interest rate adjustments",
            "moderate": "reduce money supply growth, increase resource production",
            "high": "implement price controls, reduce currency injections",
            "critical": "emergency measures: freeze prices, issue new currency, reset economy",
        }

        return {
            "detected": severity != "none",
            "severity": severity,
            "inflation_rate": round(observed_inflation * 100, 2),
            "price_index": round(self._price_index, 2),
            "target_inflation": round(self._config.inflation_rate * 100, 2),
            "max_inflation": round(self._config.max_inflation * 100, 2),
            "ticks_analyzed": len(relevant),
            "recommendation": recommendations[severity],
        }

    def stress_test(self, scenario: str) -> Dict[str, Any]:
        with self._lock:
            if self._config is None:
                return {"error": "no active economy configured"}

            scenarios = {
                "hyperinflation": self._stress_hyperinflation,
                "market_crash": self._stress_market_crash,
                "supply_shock": self._stress_supply_shock,
                "demand_surge": self._stress_demand_surge,
                "liquidity_crisis": self._stress_liquidity_crisis,
            }

            handler = scenarios.get(scenario, self._stress_default)
            result = handler()

            result["scenario"] = scenario
            result["model"] = self._config.model.value
            result["tick"] = self._tick
            result["trader_count"] = len(self._traders)
            result["resource_count"] = len(self._resources)

            return result

    def get_economy_report(self) -> Dict[str, Any]:
        with self._lock:
            if self._config is None:
                return {"status": "no_economy", "message": "no economy has been created"}

            inflation_data = self._detect_inflation_locked()

            resource_summary = {}
            for rid, res in self._resources.items():
                current_price = self._compute_current_price(res)
                resource_summary[rid] = {
                    "name": res.name,
                    "base_price": res.base_price,
                    "current_price": round(current_price, 2),
                    "price_change_pct": round(
                        ((current_price - res.base_price) / res.base_price * 100)
                        if res.base_price > 0 else 0, 2
                    ),
                    "supply": round(res.current_supply, 2),
                    "demand": round(res.current_demand, 2),
                    "category": res.category,
                }

            trader_summary = {
                "total": len(self._traders),
                "active": len([b for b in self._traders.values() if b > 0]),
                "total_wealth": round(sum(self._traders.values()), 2),
                "avg_balance": round(
                    sum(self._traders.values()) / max(1, len(self._traders)), 2
                ),
                "wealthiest": max(self._traders.values()) if self._traders else 0,
                "poorest": min(self._traders.values()) if self._traders else 0,
            }

            recent_snapshot = self._snapshots[-1] if self._snapshots else None

            return {
                "status": "active",
                "config": self._config.to_dict(),
                "inflation": inflation_data,
                "resources": resource_summary,
                "traders": trader_summary,
                "market": {
                    "condition": recent_snapshot.condition.value if recent_snapshot else "unknown",
                    "price_index": self._price_index,
                    "money_supply": self._money_supply,
                    "gini_coefficient": recent_snapshot.gini_coefficient if recent_snapshot else 0,
                    "total_transactions": len(self._transactions),
                },
                "tick": self._tick,
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_traded_value = sum(t.price * t.amount for t in self._transactions)
            unique_buyers = len(set(t.buyer for t in self._transactions if t.buyer))
            unique_sellers = len(set(t.seller for t in self._transactions if t.seller))

            flow_breakdown: Dict[str, int] = {}
            for t in self._transactions:
                ft = t.flow_type.value
                flow_breakdown[ft] = flow_breakdown.get(ft, 0) + 1

            return {
                "tick": self._tick,
                "config_name": self._config.name if self._config else "none",
                "model": self._config.model.value if self._config else "none",
                "total_resources": len(self._resources),
                "total_traders": len(self._traders),
                "total_transactions": len(self._transactions),
                "total_traded_value": round(total_traded_value, 2),
                "money_supply": round(self._money_supply, 2),
                "price_index": round(self._price_index, 2),
                "unique_buyers": unique_buyers,
                "unique_sellers": unique_sellers,
                "flow_breakdown": flow_breakdown,
                "snapshots_recorded": len(self._snapshots),
            }

    def _update_resource_supply_demand(self) -> None:
        if self._config is None:
            return

        for resource in self._resources.values():
            noise_prod = random.uniform(0.8, 1.2)
            noise_cons = random.uniform(0.8, 1.2)

            produced = resource.production_rate * noise_prod
            consumed = resource.consumption_rate * noise_cons

            if self._config.model == EconomyModel.FREE_MARKET:
                consumed *= 1.0 + random.uniform(-0.05, 0.05)
            elif self._config.model == EconomyModel.COMMAND:
                consumed = resource.consumption_rate
                produced = resource.production_rate
            elif self._config.model == EconomyModel.GIFT:
                produced *= 2.0
                consumed *= 0.5

            resource.current_supply += produced
            resource.current_demand = consumed * (1.0 + resource.scarcity)
            resource.current_supply = max(0.0, resource.current_supply - consumed)

            max_supply = resource.current_demand * 1.5
            resource.current_supply = min(resource.current_supply, max_supply)

    def _process_trader_activity(self) -> None:
        if not self._traders or not self._resources or self._config is None:
            return

        active_traders = [tid for tid, bal in self._traders.items() if bal > 0]
        if len(active_traders) < 2:
            return

        trades_this_tick = random.randint(1, max(1, len(active_traders) // 2))
        resources_list = list(self._resources.values())

        for _ in range(trades_this_tick):
            buyer_id = random.choice(active_traders)
            seller_id = random.choice([t for t in active_traders if t != buyer_id])
            resource = random.choice(resources_list)

            current_price = self._compute_current_price(resource)
            max_affordable = self._traders[buyer_id] / max(current_price, 0.01)
            trade_amount = min(
                resource.current_supply * random.uniform(0.01, 0.1),
                max_affordable,
            )
            trade_amount = max(0.1, trade_amount)

            total_cost = trade_amount * current_price

            if self._config.model == EconomyModel.GIFT:
                tax = 0.0
            else:
                tax = total_cost * self._config.transaction_tax

            if self._traders[buyer_id] >= total_cost + tax:
                self._traders[buyer_id] -= total_cost + tax
                self._traders[seller_id] += total_cost

                if tax > 0:
                    self._money_supply -= tax

                resource.current_supply -= trade_amount
                resource.current_supply = max(0.0, resource.current_supply)

                transaction = MarketTransaction(
                    resource_id=resource.id,
                    amount=trade_amount,
                    price=current_price,
                    buyer=buyer_id,
                    seller=seller_id,
                    flow_type=ResourceFlow.TRADE,
                )
                self._transactions.append(transaction)

                if len(self._transactions) > self._MAX_TRANSACTIONS:
                    self._transactions = self._transactions[-self._MAX_TRANSACTIONS:]

    def _adjust_prices(self) -> None:
        if self._config is None:
            return

        total_weighted_price = 0.0
        total_weight = 0.0

        for resource in self._resources.values():
            supply_demand_ratio = (
                resource.current_supply / max(resource.current_demand, 0.01)
            )
            volatility = random.uniform(
                -self._config.price_volatility, self._config.price_volatility
            )

            if self._config.model == EconomyModel.FREE_MARKET:
                price_pressure = (1.0 / max(supply_demand_ratio, 0.01) - 1.0) * 0.1
            elif self._config.model == EconomyModel.COMMAND:
                price_pressure = 0.0
            elif self._config.model == EconomyModel.GIFT:
                price_pressure = -0.05
            else:
                price_pressure = (1.0 / max(supply_demand_ratio, 0.01) - 1.0) * 0.05

            tick_inflation = self._config.inflation_rate * 0.05
            inflation_factor = 1.0 + tick_inflation
            new_base = resource.base_price * inflation_factor

            price_multiplier = max(0.01, 1.0 + price_pressure + volatility)
            resource.base_price = new_base * price_multiplier
            resource.base_price = max(
                resource.min_price, min(resource.max_price, resource.base_price)
            )

            new_price = self._compute_current_price(resource)
            total_weighted_price += new_price
            total_weight += 1.0

        if total_weight > 0:
            new_index = total_weighted_price / total_weight
            if self._price_index > 0:
                self._price_index = self._price_index * 0.9 + new_index * 0.1
            else:
                self._price_index = new_index

    def _update_money_supply(self) -> None:
        if self._config is None:
            return

        growth = 0.0
        for resource in self._resources.values():
            growth += resource.production_rate * 0.1

        if self._config.model == EconomyModel.COMMAND:
            growth *= 0.5
        elif self._config.model == EconomyModel.GIFT:
            growth *= 0.0

        self._money_supply += growth

    def _compute_current_price(self, resource: ResourceDef) -> float:
        supply_demand_ratio = (
            resource.current_supply / max(resource.current_demand, 0.01)
        )
        ratio_factor = 1.0 / max(supply_demand_ratio, 0.01)
        scarcity_factor = 1.0 + resource.scarcity
        elasticity_divisor = max(resource.price_elasticity, 0.1)
        price = resource.base_price * ratio_factor * scarcity_factor / elasticity_divisor
        return max(resource.min_price, min(resource.max_price, price))

    def _classify_market_condition(self) -> MarketCondition:
        if not self._snapshots:
            return MarketCondition.STABLE

        recent = self._snapshots[-min(10, len(self._snapshots)):]
        if len(recent) < 2:
            return MarketCondition.STABLE

        price_changes = []
        for i in range(1, len(recent)):
            prev = recent[i - 1].avg_price_index
            curr = recent[i].avg_price_index
            if prev > 0:
                price_changes.append((curr - prev) / prev)

        if not price_changes:
            return MarketCondition.STABLE

        avg_change = sum(price_changes) / len(price_changes)
        variance = sum((c - avg_change) ** 2 for c in price_changes) / len(price_changes)

        if variance > 0.01:
            return MarketCondition.VOLATILE
        elif avg_change > 0.05:
            return MarketCondition.INFLATIONARY
        elif avg_change < -0.05:
            return MarketCondition.DEFLATIONARY
        else:
            return MarketCondition.STABLE

    def _compute_gini(self) -> float:
        balances = sorted(self._traders.values())
        n = len(balances)
        if n == 0 or sum(balances) == 0:
            return 0.0

        total = sum(balances)
        cumulative = 0.0
        gini_sum = 0.0

        for i, balance in enumerate(balances):
            cumulative += balance
            gini_sum += (i + 1) * balance

        gini = (2 * gini_sum) / (n * total) - (n + 1) / n
        return max(0.0, min(1.0, gini))

    def _stress_hyperinflation(self) -> Dict[str, Any]:
        original_inflation = self._config.inflation_rate
        original_volatility = self._config.price_volatility

        self._config.inflation_rate = 0.50
        self._config.price_volatility = 0.30

        pre_snapshot = self._snapshots[-1] if self._snapshots else None
        pre_prices = {}
        for rid, res in self._resources.items():
            pre_prices[rid] = self._compute_current_price(res)

        for _ in range(10):
            self._simulate_tick_locked()

        post_prices = {}
        for rid, res in self._resources.items():
            post_prices[rid] = self._compute_current_price(res)

        price_impacts = {}
        for rid in pre_prices:
            if pre_prices.get(rid, 0) > 0:
                change = (post_prices[rid] - pre_prices[rid]) / pre_prices[rid] * 100
                price_impacts[rid] = round(change, 2)

        self._config.inflation_rate = original_inflation
        self._config.price_volatility = original_volatility

        return {
            "description": "rapid uncontrolled inflation simulation",
            "duration_ticks": 10,
            "pre_index": pre_snapshot.avg_price_index if pre_snapshot else 100.0,
            "post_index": round(self._price_index, 2),
            "avg_price_change_pct": round(
                sum(price_impacts.values()) / max(len(price_impacts), 1), 2
            ),
            "price_impacts": price_impacts,
            "survivable": self._price_index < 500.0,
            "recommendation": "implement strict price controls and reduce money supply",
        }

    def _stress_market_crash(self) -> Dict[str, Any]:
        pre_balances = dict(self._traders)

        for resource in self._resources.values():
            resource.base_price *= 0.01
            resource.current_demand *= 0.1

        for trader_id in self._traders:
            self._traders[trader_id] *= random.uniform(0.1, 0.3)

        self._money_supply *= 0.2

        for _ in range(5):
            self._simulate_tick_locked()

        post_balances = dict(self._traders)
        wealth_destroyed = sum(pre_balances.values()) - sum(post_balances.values())

        return {
            "description": "sudden market collapse with asset devaluation",
            "duration_ticks": 5,
            "wealth_destroyed": round(wealth_destroyed, 2),
            "wealth_destroyed_pct": round(
                (wealth_destroyed / max(sum(pre_balances.values()), 1.0)) * 100, 2
            ),
            "post_index": round(self._price_index, 2),
            "active_traders_post": len([b for b in self._traders.values() if b > 0]),
            "recommendation": "inject liquidity, provide trader bailouts, stimulate demand",
        }

    def _stress_supply_shock(self) -> Dict[str, Any]:
        affected_resources = []

        for resource in self._resources.values():
            resource.current_supply *= 0.1
            resource.production_rate *= 0.2
            affected_resources.append({
                "id": resource.id,
                "name": resource.name,
                "supply_after_shock": round(resource.current_supply, 2),
            })

        for _ in range(5):
            self._simulate_tick_locked()

        post_prices = {}
        for rid, res in self._resources.items():
            post_prices[rid] = round(self._compute_current_price(res), 2)

        return {
            "description": "sudden supply shortage across all resources",
            "duration_ticks": 5,
            "affected_resources": affected_resources,
            "post_prices": post_prices,
            "post_index": round(self._price_index, 2),
            "recommendation": "increase production capacity, find alternative resources",
        }

    def _stress_demand_surge(self) -> Dict[str, Any]:
        for resource in self._resources.values():
            resource.current_demand *= 10.0

        for trader_id in self._traders:
            self._traders[trader_id] *= random.uniform(1.5, 3.0)

        self._money_supply *= 2.0

        for _ in range(5):
            self._simulate_tick_locked()

        return {
            "description": "explosive demand increase across all resources",
            "duration_ticks": 5,
            "post_index": round(self._price_index, 2),
            "money_supply": round(self._money_supply, 2),
            "avg_trader_balance": round(
                sum(self._traders.values()) / max(len(self._traders), 1), 2
            ),
            "recommendation": "increase production to meet demand, consider price ceilings",
        }

    def _stress_liquidity_crisis(self) -> Dict[str, Any]:
        pre_transaction_volume = len(self._transactions)

        for trader_id in list(self._traders.keys()):
            self._traders[trader_id] *= random.uniform(0.0, 0.05)

        for _ in range(5):
            self._simulate_tick_locked()

        post_transaction_volume = len(self._transactions)
        frozen_traders = len([b for b in self._traders.values() if b <= 0.01])

        return {
            "description": "severe currency shortage halting all trade",
            "duration_ticks": 5,
            "transactions_during_crisis": post_transaction_volume - pre_transaction_volume,
            "frozen_traders": frozen_traders,
            "frozen_pct": round(
                (frozen_traders / max(len(self._traders), 1)) * 100, 2
            ),
            "recommendation": "issue emergency currency, provide universal basic income",
        }

    def _stress_default(self) -> Dict[str, Any]:
        return {
            "description": "generic stress test with moderate volatility",
            "error": "unknown scenario, running default mild stress",
            "recommendation": "specify a valid scenario: hyperinflation, market_crash, supply_shock, demand_surge, liquidity_crisis",
        }

    def reset(self) -> None:
        with self._lock:
            self._config = None
            self._resources = {}
            self._traders = {}
            self._transactions = []
            self._snapshots = []
            self._tick = 0
            self._price_index = 100.0
            self._money_supply = 0.0


def get_economy_simulator() -> EconomySimulator:
    return EconomySimulator.get_instance()