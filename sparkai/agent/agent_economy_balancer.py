"""
SparkLabs Agent - Economy Balancer

AI-driven economy balancing system for the SparkLabs AI-Native Game Engine.
Manages in-game currencies, resource flows, market dynamics, inflation
control, and reward balancing. Provides automated detection of economic
imbalances and generates corrective actions to maintain a healthy,
sustainable game economy.

Architecture:
  EconomyBalancerEngine (Singleton)
    |-- Currency Registry (multi-currency management, exchange rates)
    |-- Transaction Ledger (player wallet tracking, transaction history)
    |-- Market Board (dynamic pricing, supply/demand equilibrium)
    |-- Inflation Monitor (detection, severity classification, remedies)
    |-- Reward Calibrator (activity-based reward computation, sustainability)

Key Features:
  - Multi-currency system with configurable exchange rates
  - Full transaction ledger with per-player balance tracking
  - Dynamic market simulation with supply/demand-driven pricing
  - Automated inflation detection with severity analysis
  - Reward balancing with difficulty/time factoring and sustainability checks

Usage:
    balancer = get_agent_economy_balancer()
    gold = balancer.create_currency("Gold", CurrencyType.GOLD, 1000000.0)
    balancer.record_transaction("player_1", gold.currency_id, TransactionType.EARN, 500.0, "Quest reward")
    balancer.simulate_market(cycles=10)
    report = balancer.analyze_economy()
    rewards = balancer.balance_rewards("combat", difficulty=7, target_value=100.0)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class CurrencyType(Enum):
    """Types of in-game currencies supported by the economy system."""

    GOLD = "gold"
    GEMS = "gems"
    CREDITS = "credits"
    TOKENS = "tokens"
    ESSENCE = "essence"
    SOULS = "souls"
    CRYSTALS = "crystals"
    REPUTATION = "reputation"
    HONOR = "honor"
    ENERGY = "energy"


class TransactionType(Enum):
    """Categories of economic transactions within the game economy."""

    EARN = "earn"
    SPEND = "spend"
    TRANSFER = "transfer"
    TAX = "tax"
    INTEREST = "interest"
    REWARD = "reward"
    PENALTY = "penalty"
    REFUND = "refund"
    TRADE = "trade"


class EconomyState(Enum):
    """Macroeconomic states describing the overall health of the economy."""

    STABLE = "stable"
    INFLATION = "inflation"
    DEFLATION = "deflation"
    RECESSION = "recession"
    BOOM = "boom"
    VOLATILE = "volatile"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class Currency:
    """Represents a single currency type within the game economy."""

    currency_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    currency_type: CurrencyType = CurrencyType.GOLD
    total_supply: float = 0.0
    circulation: float = 0.0
    reserves: float = 0.0
    exchange_rate: float = 1.0
    inflation_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency_id": self.currency_id,
            "name": self.name,
            "currency_type": self.currency_type.value,
            "total_supply": round(self.total_supply, 2),
            "circulation": round(self.circulation, 2),
            "reserves": round(self.reserves, 2),
            "exchange_rate": round(self.exchange_rate, 4),
            "inflation_rate": round(self.inflation_rate, 4),
            "created_at": self.created_at,
        }


@dataclass
class Transaction:
    """Records a single economic transaction in the player ledger."""

    tx_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    currency_id: str = ""
    transaction_type: TransactionType = TransactionType.EARN
    amount: float = 0.0
    balance_before: float = 0.0
    balance_after: float = 0.0
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "player_id": self.player_id,
            "currency_id": self.currency_id,
            "transaction_type": self.transaction_type.value,
            "amount": round(self.amount, 2),
            "balance_before": round(self.balance_before, 2),
            "balance_after": round(self.balance_after, 2),
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class MarketItem:
    """Represents a tradeable item on the dynamic market board."""

    item_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: str = ""
    base_price: float = 0.0
    current_price: float = 0.0
    supply: float = 0.0
    demand: float = 0.0
    price_history: Deque[float] = field(default_factory=lambda: deque(maxlen=200))
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "base_price": round(self.base_price, 2),
            "current_price": round(self.current_price, 2),
            "supply": round(self.supply, 2),
            "demand": round(self.demand, 2),
            "price_history": [round(p, 2) for p in list(self.price_history)[-20:]],
            "last_updated": self.last_updated,
        }


@dataclass
class InflationReport:
    """Detailed analysis of inflation conditions within the economy."""

    state: EconomyState = EconomyState.STABLE
    inflation_rate: float = 0.0
    severity: str = "none"
    affected_currencies: List[str] = field(default_factory=list)
    price_trend: str = "stable"
    recommended_action: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "inflation_rate": round(self.inflation_rate, 4),
            "severity": self.severity,
            "affected_currencies": list(self.affected_currencies),
            "price_trend": self.price_trend,
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }


# =============================================================================
# EconomyBalancerEngine (Singleton)
# =============================================================================


class EconomyBalancerEngine:
    """
    AI-driven economy balancing engine for game worlds.

    Manages the complete economic lifecycle: currency creation, transaction
    recording, market simulation, inflation detection, and reward calibration.
    Operates as a singleton to ensure consistent economic state across all
    game subsystems.

    Usage:
        engine = get_agent_economy_balancer()
        gold = engine.create_currency("Gold", CurrencyType.GOLD, 1000000.0)
        engine.record_transaction("player_1", gold.currency_id, TransactionType.EARN, 500.0, "Quest reward")
        state = engine.get_economy_state()
    """

    _instance: Optional["EconomyBalancerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # --- Constants ---
    _MAX_PRICE_HISTORY: int = 200
    _MAX_TRANSACTION_HISTORY: int = 10000
    _DEFAULT_INFLATION_TARGET: float = 0.02
    _PRICE_FLOOR: float = 0.01
    _PRICE_CEILING: float = 1_000_000_000.0
    _INFLATION_WARNING_THRESHOLD: float = 0.05
    _INFLATION_SEVERE_THRESHOLD: float = 0.15
    _DEFLATION_WARNING_THRESHOLD: float = -0.03
    _DEFLATION_SEVERE_THRESHOLD: float = -0.10
    _VOLATILITY_THRESHOLD: float = 0.08
    _SUPPLY_DEMAND_IMBALANCE_RATIO: float = 3.0
    _SUSTAINABILITY_DECAY_RATE: float = 0.01
    _REWARD_SCALING_FACTOR: float = 1.2

    def __new__(cls) -> "EconomyBalancerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EconomyBalancerEngine":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        # Currency registry: currency_id -> Currency
        self._currencies: Dict[str, Currency] = {}

        # Player balances: player_id -> {currency_id -> float}
        self._balances: Dict[str, Dict[str, float]] = {}

        # Transaction ledger
        self._transactions: Deque[Transaction] = deque(maxlen=self._MAX_TRANSACTION_HISTORY)

        # Market board: item_id -> MarketItem
        self._market_items: Dict[str, MarketItem] = {}

        # Exchange rates: (from_currency_id, to_currency_id) -> float
        self._exchange_rates: Dict[Tuple[str, str], float] = {}

        # Economy-wide metrics
        self._total_money_supply: float = 0.0
        self._total_circulation: float = 0.0
        self._global_inflation: float = 0.0
        self._market_volatility: float = 0.0
        self._cycle_count: int = 0

        # Faucet and sink tracking
        self._total_earned: float = 0.0
        self._total_spent: float = 0.0
        self._total_taxed: float = 0.0

        # Reward calibration history
        self._reward_history: Deque[Dict[str, Any]] = deque(maxlen=500)

        # Stats
        self._stats: Dict[str, Any] = {
            "total_currencies_created": 0,
            "total_transactions": 0,
            "total_market_items": 0,
            "total_cycles_simulated": 0,
            "total_inflation_checks": 0,
            "total_rewards_calibrated": 0,
        }

    # =========================================================================
    # Currency Management
    # =========================================================================

    def create_currency(
        self,
        name: str,
        currency_type: CurrencyType,
        initial_supply: float,
    ) -> Currency:
        """
        Create a new currency and register it in the economy.

        Args:
            name: Human-readable name of the currency.
            currency_type: The CurrencyType enum value.
            initial_supply: Total initial money supply for this currency.

        Returns:
            The newly created Currency object.
        """
        if isinstance(currency_type, str):
            try:
                currency_type = CurrencyType(currency_type)
            except ValueError:
                currency_type = CurrencyType.GOLD

        currency = Currency(
            name=name,
            currency_type=currency_type,
            total_supply=initial_supply,
            circulation=initial_supply * 0.7,
            reserves=initial_supply * 0.3,
            exchange_rate=1.0,
            inflation_rate=self._DEFAULT_INFLATION_TARGET,
        )
        self._currencies[currency.currency_id] = currency
        self._exchange_rates[(currency.currency_id, currency.currency_id)] = 1.0
        self._total_money_supply += initial_supply
        self._total_circulation += currency.circulation
        self._stats["total_currencies_created"] += 1
        return currency

    def set_exchange_rate(
        self,
        from_currency_id: str,
        to_currency_id: str,
        rate: float,
    ) -> Optional[Currency]:
        """
        Set the exchange rate between two currencies.

        Args:
            from_currency_id: The source currency ID.
            to_currency_id: The target currency ID.
            rate: The exchange rate (1 unit of from_currency = rate units of to_currency).

        Returns:
            The source Currency if both currencies exist, None otherwise.
        """
        from_currency = self._currencies.get(from_currency_id)
        to_currency = self._currencies.get(to_currency_id)
        if from_currency is None or to_currency is None:
            return None
        if rate <= 0:
            return None

        self._exchange_rates[(from_currency_id, to_currency_id)] = rate
        self._exchange_rates[(to_currency_id, from_currency_id)] = 1.0 / rate
        return from_currency

    # =========================================================================
    # Transaction Recording
    # =========================================================================

    def record_transaction(
        self,
        player_id: str,
        currency_id: str,
        transaction_type: TransactionType,
        amount: float,
        description: str = "",
    ) -> Optional[Transaction]:
        """
        Record a financial transaction for a player.

        Args:
            player_id: The unique identifier of the player.
            currency_id: The currency involved in the transaction.
            transaction_type: The type of transaction (EARN, SPEND, etc.).
            amount: The transaction amount (always positive).
            description: Optional description of the transaction.

        Returns:
            The recorded Transaction, or None if the currency is not found.
        """
        currency = self._currencies.get(currency_id)
        if currency is None:
            return None

        if isinstance(transaction_type, str):
            try:
                transaction_type = TransactionType(transaction_type)
            except ValueError:
                transaction_type = TransactionType.EARN

        # Ensure player wallet exists
        if player_id not in self._balances:
            self._balances[player_id] = {}

        if currency_id not in self._balances[player_id]:
            self._balances[player_id][currency_id] = 0.0

        balance_before = self._balances[player_id][currency_id]

        # Apply transaction based on type
        effective_amount = amount
        if transaction_type in (TransactionType.EARN, TransactionType.REWARD, TransactionType.INTEREST, TransactionType.REFUND):
            self._balances[player_id][currency_id] += amount
            self._total_earned += amount
            currency.circulation += amount
        elif transaction_type in (TransactionType.SPEND, TransactionType.TAX, TransactionType.PENALTY):
            self._balances[player_id][currency_id] -= amount
            self._total_spent += amount
            currency.circulation -= amount
            if transaction_type == TransactionType.TAX:
                self._total_taxed += amount
                currency.reserves += amount
        elif transaction_type == TransactionType.TRANSFER:
            self._balances[player_id][currency_id] -= amount
        elif transaction_type == TransactionType.TRADE:
            self._balances[player_id][currency_id] -= amount
            self._total_spent += amount

        balance_after = self._balances[player_id][currency_id]

        transaction = Transaction(
            player_id=player_id,
            currency_id=currency_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
        )
        self._transactions.append(transaction)
        self._stats["total_transactions"] += 1

        # Update total circulation
        self._total_circulation = sum(
            c.circulation for c in self._currencies.values()
        )

        return transaction

    def get_balance(self, player_id: str, currency_id: str) -> float:
        """
        Get the current balance for a player in a specific currency.

        Args:
            player_id: The unique identifier of the player.
            currency_id: The currency to query.

        Returns:
            The player's balance, or 0.0 if no balance exists.
        """
        return self._balances.get(player_id, {}).get(currency_id, 0.0)

    # =========================================================================
    # Market Management
    # =========================================================================

    def add_market_item(
        self,
        name: str,
        category: str,
        base_price: float,
        supply: float = 100.0,
    ) -> MarketItem:
        """
        Add a new item to the dynamic market board.

        Args:
            name: Display name of the market item.
            category: Item category for grouping.
            base_price: The equilibrium/base price.
            supply: Initial supply quantity.

        Returns:
            The newly created MarketItem.
        """
        demand = supply * random.uniform(0.8, 1.5)
        item = MarketItem(
            name=name,
            category=category,
            base_price=base_price,
            current_price=base_price,
            supply=supply,
            demand=demand,
        )
        item.price_history.append(base_price)
        self._market_items[item.item_id] = item
        self._stats["total_market_items"] += 1
        return item

    def update_market_price(self, item_id: str) -> Optional[MarketItem]:
        """
        Recalculate the price of a market item based on current supply and demand.

        The price adjusts toward equilibrium: when demand exceeds supply, the
        price rises; when supply exceeds demand, the price falls. A random
        volatility component simulates market noise.

        Args:
            item_id: The ID of the market item to update.

        Returns:
            The updated MarketItem, or None if not found.
        """
        item = self._market_items.get(item_id)
        if item is None:
            return None

        # Compute supply/demand ratio
        if item.demand > 0:
            ratio = item.supply / item.demand
        else:
            ratio = item.supply / 0.01

        # Price adjustment: short supply drives price up, oversupply drives it down
        if ratio < 1.0:
            # Scarcity: price rises
            scarcity_factor = (1.0 - ratio) * 0.3
            price_change = item.current_price * scarcity_factor
        elif ratio > 1.0:
            # Glut: price falls
            glut_factor = min((ratio - 1.0) * 0.2, 0.5)
            price_change = -item.current_price * glut_factor
        else:
            price_change = 0.0

        # Add random volatility
        volatility = random.uniform(-0.03, 0.03) * item.current_price
        new_price = item.current_price + price_change + volatility

        # Clamp within bounds
        new_price = max(self._PRICE_FLOOR, min(self._PRICE_CEILING, new_price))

        # Mean reversion toward base price
        reversion_strength = 0.02
        new_price += (item.base_price - new_price) * reversion_strength

        item.current_price = round(new_price, 2)
        item.price_history.append(item.current_price)
        item.last_updated = time.time()

        return item

    # =========================================================================
    # Market Simulation
    # =========================================================================

    def simulate_market(self, cycles: int = 1) -> Dict[str, Any]:
        """
        Run a market simulation over the specified number of cycles.

        Each cycle performs:
          1. Random supply and demand fluctuations for all market items.
          2. Price recalculation based on supply/demand equilibrium.
          3. Simulated player transactions at current prices.
          4. Supply chain effect propagation across related items.
          5. Market health metric computation.

        Args:
            cycles: Number of simulation cycles to run.

        Returns:
            A dictionary containing the simulation report with price trends,
            market health, volatility, and affected items.
        """
        if not self._market_items:
            self.add_market_item("Default Item", "general", 10.0, 100.0)

        price_changes: List[float] = []
        affected_items: List[str] = []
        total_volume: float = 0.0

        for _ in range(cycles):
            self._cycle_count += 1
            self._stats["total_cycles_simulated"] += 1

            # Step 1: Fluctuate supply and demand
            for item in self._market_items.values():
                supply_shock = item.supply * random.uniform(-0.08, 0.12)
                demand_shock = item.demand * random.uniform(-0.06, 0.10)
                item.supply = max(0.0, item.supply + supply_shock)
                item.demand = max(0.0, item.demand + demand_shock)

            # Step 2: Update prices
            for item in self._market_items.values():
                old_price = item.current_price
                self.update_market_price(item.item_id)
                if old_price > 0:
                    change_pct = (item.current_price - old_price) / old_price
                    price_changes.append(change_pct)
                    if abs(change_pct) > 0.05:
                        affected_items.append(item.name)

                # Simulate transaction volume
                tx_volume = min(item.supply, item.demand) * random.uniform(0.1, 0.3)
                total_volume += tx_volume

            # Step 3: Supply chain effects - propagate price changes to related categories
            self._propagate_supply_chain_effects()

            # Step 4: Update global metrics
            if price_changes:
                self._global_inflation = sum(price_changes) / len(price_changes)
                self._market_volatility = (
                    sum(abs(pc - self._global_inflation) for pc in price_changes)
                    / max(len(price_changes), 1)
                )

        # Generate report
        market_health = self._compute_market_health()
        economy_state = self.get_economy_state()

        report = {
            "cycles_run": cycles,
            "total_cycles": self._cycle_count,
            "economy_state": economy_state.value,
            "market_health": round(market_health, 4),
            "market_volatility": round(self._market_volatility, 4),
            "global_inflation": round(self._global_inflation, 4),
            "total_items": len(self._market_items),
            "average_price_change": (
                round(sum(price_changes) / max(len(price_changes), 1), 4)
                if price_changes
                else 0.0
            ),
            "items_with_significant_change": len(set(affected_items)),
            "simulated_volume": round(total_volume, 2),
            "supply_chain_propagations": self._cycle_count,
        }

        return report

    def _propagate_supply_chain_effects(self) -> None:
        """
        Propagate price changes through the supply chain.

        Items in the same category experience correlated price movements,
        simulating real-world supply chain interdependencies.
        """
        categories: Dict[str, List[MarketItem]] = {}
        for item in self._market_items.values():
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)

        for cat_items in categories.values():
            if len(cat_items) < 2:
                continue
            avg_price_change = 0.0
            for item in cat_items:
                if len(item.price_history) >= 2:
                    old = item.price_history[-2]
                    new = item.price_history[-1]
                    if old > 0:
                        avg_price_change += (new - old) / old
            avg_price_change /= len(cat_items)

            # Propagate partial effect to each item
            for item in cat_items:
                propagation = item.current_price * avg_price_change * 0.15
                item.current_price = max(
                    self._PRICE_FLOOR,
                    min(self._PRICE_CEILING, item.current_price + propagation),
                )

    def _compute_market_health(self) -> float:
        """
        Compute a composite market health score from 0.0 to 1.0.

        Factors:
          - Supply/demand balance across all items
          - Inflation stability (closeness to target)
          - Market diversity (number of items/categories)
          - Volatility (lower is healthier)

        Returns:
            A float between 0.0 (unhealthy) and 1.0 (healthy).
        """
        if not self._market_items:
            return 0.5

        # Supply/demand balance
        total_supply = sum(item.supply for item in self._market_items.values())
        total_demand = sum(item.demand for item in self._market_items.values())
        if total_supply + total_demand > 0:
            balance_score = 1.0 - abs(total_supply - total_demand) / (total_supply + total_demand)
        else:
            balance_score = 0.5

        # Inflation stability
        inflation_deviation = abs(self._global_inflation - self._DEFAULT_INFLATION_TARGET)
        inflation_score = max(0.0, 1.0 - inflation_deviation / 0.2)

        # Diversity
        categories = set(item.category for item in self._market_items.values())
        diversity_score = min(1.0, len(categories) / 5.0)

        # Volatility
        volatility_score = max(0.0, 1.0 - self._market_volatility / 0.15)

        return (
            balance_score * 0.35
            + inflation_score * 0.25
            + diversity_score * 0.15
            + volatility_score * 0.25
        )

    # =========================================================================
    # Economy Analysis
    # =========================================================================

    def analyze_economy(self) -> Dict[str, Any]:
        """
        Perform a comprehensive analysis of the current economy state.

        Calculates total money supply, identifies currency faucets and sinks,
        detects inflation risks, and suggests balancing adjustments.

        Returns:
            A dictionary with detailed economic analysis including money supply,
            faucet/sink ratios, inflation risk assessment, and recommendations.
        """
        # Total money supply
        total_supply = sum(c.total_supply for c in self._currencies.values())
        total_circulation = sum(c.circulation for c in self._currencies.values())
        total_reserves = sum(c.reserves for c in self._currencies.values())

        # Faucet vs sink analysis
        faucet_total = self._total_earned
        sink_total = self._total_spent
        if sink_total > 0:
            faucet_sink_ratio = faucet_total / sink_total
        else:
            faucet_sink_ratio = faucet_total if faucet_total > 0 else 1.0

        # Identify faucet/sink imbalance
        if faucet_sink_ratio > 1.5:
            faucet_sink_status = "faucet_heavy"
            faucet_sink_detail = "More currency entering than leaving; risk of inflation."
        elif faucet_sink_ratio < 0.67:
            faucet_sink_status = "sink_heavy"
            faucet_sink_detail = "More currency leaving than entering; risk of deflation."
        else:
            faucet_sink_status = "balanced"
            faucet_sink_detail = "Faucet and sink flows are reasonably balanced."

        # Inflation risk assessment
        inflation_risk = self._assess_inflation_risk()

        # Currency-specific analysis
        currency_breakdown = []
        for currency in self._currencies.values():
            velocity = currency.circulation / max(currency.total_supply, 1.0)
            currency_breakdown.append({
                "currency_id": currency.currency_id,
                "name": currency.name,
                "type": currency.currency_type.value,
                "total_supply": round(currency.total_supply, 2),
                "circulation": round(currency.circulation, 2),
                "reserves": round(currency.reserves, 2),
                "velocity": round(velocity, 4),
                "inflation_rate": round(currency.inflation_rate, 4),
            })

        # Market item analysis
        item_analysis = []
        for item in self._market_items.values():
            if item.demand > 0:
                supply_demand_ratio = item.supply / item.demand
            else:
                supply_demand_ratio = float("inf")
            if item.base_price > 0:
                price_deviation = (item.current_price - item.base_price) / item.base_price
            else:
                price_deviation = 0.0
            item_analysis.append({
                "item_id": item.item_id,
                "name": item.name,
                "category": item.category,
                "current_price": round(item.current_price, 2),
                "base_price": round(item.base_price, 2),
                "price_deviation_pct": round(price_deviation * 100, 2),
                "supply_demand_ratio": round(supply_demand_ratio, 4) if supply_demand_ratio != float("inf") else "infinite",
            })

        # Suggestions
        suggestions = self._generate_balancing_suggestions(
            faucet_sink_ratio, inflation_risk
        )

        return {
            "economy_state": self.get_economy_state().value,
            "total_money_supply": round(total_supply, 2),
            "total_circulation": round(total_circulation, 2),
            "total_reserves": round(total_reserves, 2),
            "faucet_total": round(faucet_total, 2),
            "sink_total": round(sink_total, 2),
            "faucet_sink_ratio": round(faucet_sink_ratio, 4),
            "faucet_sink_status": faucet_sink_status,
            "faucet_sink_detail": faucet_sink_detail,
            "global_inflation": round(self._global_inflation, 4),
            "inflation_risk": inflation_risk,
            "market_volatility": round(self._market_volatility, 4),
            "num_currencies": len(self._currencies),
            "num_market_items": len(self._market_items),
            "num_transactions": self._stats["total_transactions"],
            "currency_breakdown": currency_breakdown,
            "item_analysis": item_analysis[:20],
            "suggestions": suggestions,
        }

    def _assess_inflation_risk(self) -> Dict[str, Any]:
        """
        Assess the current inflation risk level.

        Returns:
            A dictionary with risk level, trend direction, and contributing factors.
        """
        risk_level = "low"
        factors = []

        if self._global_inflation > self._INFLATION_SEVERE_THRESHOLD:
            risk_level = "critical"
            factors.append("global_inflation_severe")
        elif self._global_inflation > self._INFLATION_WARNING_THRESHOLD:
            risk_level = "high"
            factors.append("global_inflation_high")
        elif self._global_inflation < self._DEFLATION_SEVERE_THRESHOLD:
            risk_level = "critical"
            factors.append("global_deflation_severe")
        elif self._global_inflation < self._DEFLATION_WARNING_THRESHOLD:
            risk_level = "high"
            factors.append("global_deflation_moderate")

        # Check currency-specific inflation
        for currency in self._currencies.values():
            if currency.inflation_rate > self._INFLATION_SEVERE_THRESHOLD:
                factors.append(f"currency_{currency.name}_inflation_severe")
                if risk_level != "critical":
                    risk_level = "high"
            elif currency.inflation_rate > self._INFLATION_WARNING_THRESHOLD:
                factors.append(f"currency_{currency.name}_inflation_moderate")

        # Check supply/demand imbalance
        for item in self._market_items.values():
            if item.demand > 0 and item.supply / item.demand < 0.2:
                factors.append(f"scarcity_{item.name}")
                if risk_level not in ("critical", "high"):
                    risk_level = "moderate"

        if not factors:
            risk_level = "low"

        # Determine trend
        if self._global_inflation > self._DEFAULT_INFLATION_TARGET + 0.01:
            trend = "rising"
        elif self._global_inflation < self._DEFAULT_INFLATION_TARGET - 0.01:
            trend = "falling"
        else:
            trend = "stable"

        return {
            "risk_level": risk_level,
            "trend": trend,
            "contributing_factors": factors,
            "factor_count": len(factors),
        }

    def _generate_balancing_suggestions(
        self,
        faucet_sink_ratio: float,
        inflation_risk: Dict[str, Any],
    ) -> List[str]:
        """
        Generate balancing suggestions based on current economic indicators.

        Args:
            faucet_sink_ratio: Ratio of total earned to total spent.
            inflation_risk: Inflation risk assessment dictionary.

        Returns:
            A list of suggestion strings.
        """
        suggestions: List[str] = []

        if faucet_sink_ratio > 1.5:
            suggestions.append(
                "Reduce currency faucets: lower quest rewards by 15-25%, "
                "decrease loot drop values, or cap daily earning limits."
            )
            suggestions.append(
                "Add currency sinks: introduce repair costs, listing fees, "
                "or consumable purchasable items for high-level players."
            )
        elif faucet_sink_ratio < 0.67:
            suggestions.append(
                "Increase currency faucets: boost rewards for activities, "
                "add daily login bonuses, or increase sell values for items."
            )
            suggestions.append(
                "Reduce currency sinks: lower tax rates, decrease repair costs, "
                "or offer rebates on regular purchases."
            )

        if inflation_risk["risk_level"] in ("high", "critical"):
            suggestions.append(
                "Adjust base prices upward for commonly traded items to "
                "counteract inflation-driven devaluation."
            )
            suggestions.append(
                "Implement dynamic pricing that adjusts vendor prices based "
                "on the current inflation rate."
            )

        if self._market_volatility > self._VOLATILITY_THRESHOLD:
            suggestions.append(
                "Stabilize market by introducing price floors/ceilings on "
                "critical items or adding market-maker NPCs."
            )

        if len(self._market_items) < 5:
            suggestions.append(
                "Expand the market with more tradeable items across diverse "
                "categories to improve economic resilience."
            )

        if not suggestions:
            suggestions.append(
                "Economy appears balanced. Continue monitoring and maintain "
                "current faucet/sink ratios."
            )

        return suggestions

    # =========================================================================
    # Inflation Detection
    # =========================================================================

    def detect_inflation(self) -> Dict[str, Any]:
        """
        Run a dedicated inflation detection pass on the current economy.

        Analyzes price trends, currency velocity, and supply/demand ratios
        to classify the current inflation state and severity.

        Returns:
            A dictionary with the inflation state, rate, severity,
            affected currencies, and recommended actions.
        """
        self._stats["total_inflation_checks"] += 1

        # Determine economy state
        state = self.get_economy_state()

        # Severity classification
        abs_inflation = abs(self._global_inflation)
        if abs_inflation > self._INFLATION_SEVERE_THRESHOLD:
            severity = "severe"
        elif abs_inflation > self._INFLATION_WARNING_THRESHOLD:
            severity = "moderate"
        elif abs_inflation > self._DEFAULT_INFLATION_TARGET:
            severity = "mild"
        else:
            severity = "none"

        # Affected currencies
        affected = []
        for currency in self._currencies.values():
            if abs(currency.inflation_rate) > self._INFLATION_WARNING_THRESHOLD:
                affected.append(currency.name)

        # Price trend
        if self._global_inflation > self._DEFAULT_INFLATION_TARGET + 0.01:
            trend = "upward"
        elif self._global_inflation < self._DEFAULT_INFLATION_TARGET - 0.01:
            trend = "downward"
        else:
            trend = "stable"

        # Recommended action
        if state == EconomyState.INFLATION:
            if severity == "severe":
                action = (
                    "Emergency measures: immediately reduce all currency faucets "
                    "by 50%, introduce emergency sinks (one-time taxes), and "
                    "freeze new currency creation."
                )
            else:
                action = (
                    "Gradually reduce currency rewards by 10-20% and increase "
                    "sink costs. Monitor weekly for improvements."
                )
        elif state == EconomyState.DEFLATION:
            action = (
                "Increase currency injection: boost rewards by 15-25%, add "
                "stimulus packages for players, and reduce sink costs."
            )
        elif state == EconomyState.VOLATILE:
            action = (
                "Stabilize markets: implement price bands, reduce random "
                "fluctuation magnitude, and add market-maker NPCs."
            )
        else:
            action = "No action needed. Maintain current monetary policy."

        report = InflationReport(
            state=state,
            inflation_rate=self._global_inflation,
            severity=severity,
            affected_currencies=affected,
            price_trend=trend,
            recommended_action=action,
        )

        return report.to_dict()

    # =========================================================================
    # Reward Balancing
    # =========================================================================

    def balance_rewards(
        self,
        activity_type: str,
        difficulty: int,
        target_value: float,
    ) -> Dict[str, Any]:
        """
        Calculate appropriate rewards for player activities.

        Factors in difficulty, time investment estimates, current economy
        state, and sustainability to prevent reward inflation while keeping
        rewards meaningful for players.

        Args:
            activity_type: Type of activity (e.g., 'combat', 'crafting', 'quest').
            difficulty: Difficulty rating from 1 (trivial) to 10 (impossible).
            target_value: The desired base reward value.

        Returns:
            A dictionary with the computed reward, breakdown, and sustainability
            metrics.
        """
        self._stats["total_rewards_calibrated"] += 1

        # Clamp difficulty
        difficulty = max(1, min(10, difficulty))

        # Base difficulty scaling: exponential curve
        difficulty_multiplier = 1.0 + (difficulty - 1) * 0.25
        if difficulty >= 7:
            difficulty_multiplier *= 1.3  # Bonus for high difficulty
        if difficulty >= 9:
            difficulty_multiplier *= 1.2  # Extra bonus for extreme difficulty

        # Activity type modifiers
        activity_modifiers = {
            "combat": 1.0,
            "crafting": 0.8,
            "quest": 1.1,
            "exploration": 0.7,
            "trading": 0.9,
            "social": 0.5,
            "pvp": 1.3,
            "raid": 1.5,
            "dungeon": 1.2,
            "gathering": 0.6,
            "achievement": 1.4,
            "daily": 0.6,
            "weekly": 1.8,
            "event": 1.2,
        }
        activity_modifier = activity_modifiers.get(activity_type, 1.0)

        # Economy state adjustment
        economy_state = self.get_economy_state()
        economy_modifier = 1.0
        if economy_state == EconomyState.INFLATION:
            economy_modifier = 0.85  # Reduce rewards during inflation
        elif economy_state == EconomyState.DEFLATION:
            economy_modifier = 1.15  # Increase rewards during deflation
        elif economy_state == EconomyState.BOOM:
            economy_modifier = 1.05  # Slight boost during boom
        elif economy_state == EconomyState.RECESSION:
            economy_modifier = 0.9  # Reduce during recession

        # Sustainability check: prevent reward inflation over time
        sustainability_factor = self._compute_sustainability_factor(activity_type)

        # Compute final reward
        base_reward = target_value * difficulty_multiplier * activity_modifier
        economy_adjusted = base_reward * economy_modifier
        final_reward = economy_adjusted * sustainability_factor

        final_reward = round(final_reward, 2)

        # Record in history
        reward_entry = {
            "activity_type": activity_type,
            "difficulty": difficulty,
            "target_value": target_value,
            "final_reward": final_reward,
            "economy_state": economy_state.value,
            "timestamp": time.time(),
        }
        self._reward_history.append(reward_entry)

        # Build breakdown
        breakdown = {
            "activity_type": activity_type,
            "difficulty": difficulty,
            "target_value": target_value,
            "computed_reward": final_reward,
            "difficulty_multiplier": round(difficulty_multiplier, 4),
            "activity_modifier": round(activity_modifier, 4),
            "economy_modifier": round(economy_modifier, 4),
            "sustainability_factor": round(sustainability_factor, 4),
            "economy_state": economy_state.value,
            "breakdown": (
                f"{target_value} (base) × {difficulty_multiplier:.2f} (difficulty) "
                f"× {activity_modifier:.2f} (activity) × {economy_modifier:.2f} "
                f"(economy) × {sustainability_factor:.2f} (sustainability) "
                f"= {final_reward}"
            ),
        }

        return breakdown

    def _compute_sustainability_factor(self, activity_type: str) -> float:
        """
        Compute a sustainability factor to prevent reward inflation over time.

        Tracks reward history per activity type and reduces rewards if the
        same activity has been rewarded too frequently, preventing players
        from farming the same activity to inflate the economy.

        Args:
            activity_type: The type of activity being rewarded.

        Returns:
            A sustainability multiplier between 0.5 and 1.0.
        """
        # Count recent rewards of the same type
        recent_same_type = sum(
            1 for r in self._reward_history
            if r["activity_type"] == activity_type
        )

        if recent_same_type == 0:
            return 1.0

        # Diminishing returns: each additional reward of the same type
        # slightly reduces the factor
        decay = 1.0 / (1.0 + recent_same_type * self._SUSTAINABILITY_DECAY_RATE)

        # Ensure a floor so rewards never become worthless
        return max(0.5, decay)

    # =========================================================================
    # Economy State Detection
    # =========================================================================

    def get_economy_state(self) -> EconomyState:
        """
        Determine the current macroeconomic state.

        Classification rules:
          - STABLE: Inflation within +/-2% of target, low volatility.
          - INFLATION: Inflation above 5% warning threshold.
          - DEFLATION: Inflation below -3% warning threshold.
          - RECESSION: Low market activity and falling prices.
          - BOOM: High market activity and rising prices within tolerance.
          - VOLATILE: High price volatility regardless of trend.

        Returns:
            The current EconomyState enum value.
        """
        if self._market_volatility > self._VOLATILITY_THRESHOLD:
            return EconomyState.VOLATILE

        if self._global_inflation > self._INFLATION_WARNING_THRESHOLD:
            # Check if it's a boom or inflation
            if self._global_inflation < self._INFLATION_SEVERE_THRESHOLD:
                # Check market activity level
                total_activity = (
                    self._total_earned + self._total_spent
                )
                if total_activity > sum(
                    c.total_supply * 0.3 for c in self._currencies.values()
                ):
                    return EconomyState.BOOM
            return EconomyState.INFLATION

        if self._global_inflation < self._DEFLATION_WARNING_THRESHOLD:
            # Check if it's a recession or deflation
            total_activity = self._total_earned + self._total_spent
            if total_activity < sum(
                c.total_supply * 0.1 for c in self._currencies.values()
            ):
                return EconomyState.RECESSION
            return EconomyState.DEFLATION

        return EconomyState.STABLE

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the economy balancer.

        Returns:
            A dictionary with counts, metrics, and state information.
        """
        total_players = len(self._balances)
        total_balances = sum(
            len(wallet) for wallet in self._balances.values()
        )

        # Compute average player balance
        all_balances: List[float] = []
        for wallet in self._balances.values():
            for balance in wallet.values():
                all_balances.append(balance)
        avg_balance = (
            sum(all_balances) / len(all_balances) if all_balances else 0.0
        )

        return {
            "economy_state": self.get_economy_state().value,
            "total_currencies": len(self._currencies),
            "total_currencies_created": self._stats["total_currencies_created"],
            "total_transactions": self._stats["total_transactions"],
            "total_market_items": self._stats["total_market_items"],
            "total_cycles_simulated": self._stats["total_cycles_simulated"],
            "total_inflation_checks": self._stats["total_inflation_checks"],
            "total_rewards_calibrated": self._stats["total_rewards_calibrated"],
            "total_money_supply": round(self._total_money_supply, 2),
            "total_circulation": round(self._total_circulation, 2),
            "total_earned": round(self._total_earned, 2),
            "total_spent": round(self._total_spent, 2),
            "total_taxed": round(self._total_taxed, 2),
            "global_inflation": round(self._global_inflation, 4),
            "market_volatility": round(self._market_volatility, 4),
            "total_players": total_players,
            "total_player_balances": total_balances,
            "average_player_balance": round(avg_balance, 2),
            "exchange_rate_pairs": len(self._exchange_rates),
            "reward_history_size": len(self._reward_history),
            "transaction_history_size": len(self._transactions),
        }

    def reset(self) -> None:
        """Reset the entire economy balancer to its initial state."""
        self._currencies.clear()
        self._balances.clear()
        self._transactions.clear()
        self._market_items.clear()
        self._exchange_rates.clear()
        self._reward_history.clear()
        self._total_money_supply = 0.0
        self._total_circulation = 0.0
        self._global_inflation = 0.0
        self._market_volatility = 0.0
        self._cycle_count = 0
        self._total_earned = 0.0
        self._total_spent = 0.0
        self._total_taxed = 0.0
        self._stats = {
            "total_currencies_created": 0,
            "total_transactions": 0,
            "total_market_items": 0,
            "total_cycles_simulated": 0,
            "total_inflation_checks": 0,
            "total_rewards_calibrated": 0,
        }


# =============================================================================
# Module-level accessor
# =============================================================================


def get_agent_economy_balancer() -> EconomyBalancerEngine:
    """Get or create the singleton EconomyBalancerEngine instance."""
    return EconomyBalancerEngine.get_instance()