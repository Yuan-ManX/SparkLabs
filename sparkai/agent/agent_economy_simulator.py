"""
SparkLabs Agent - Economy Simulator

Game economy simulation and balancing engine for the SparkLabs AI-Native
Game Engine. Models dynamic markets, multi-currency systems, trade networks,
production chains, and macroeconomic indicators. Provides automated imbalance
detection and balancing suggestions to keep game economies healthy and engaging.

Architecture:
  AgentEconomySimulator (Singleton)
    |-- MarketEngine (supply/demand curves, price computation, arbitrage)
    |-- CurrencySystem (multiple currencies, exchange rates, inflation)
    |-- TradeNetwork (trade routes, merchant NPCs, tariffs)
    |-- ProductionChain (resource transformation recipes, crafting)
    |-- EconomyMetrics (GDP tracking, wealth distribution, market health)
    |-- BalanceAdvisor (detect imbalances, suggest parameter adjustments)

Key Features:
  - Dynamic supply/demand curves with price elasticity and equilibrium
  - Multi-currency system with floating exchange rates and inflation modeling
  - Trade network simulation with routes, tariffs, and embargoes
  - Production chain modeling with tiered recipes and crafting costs
  - Macroeconomic tracking: GDP, Gini coefficient, inflation, market health
  - Automated imbalance detection and parameter tuning suggestions

Usage:
    sim = get_agent_economy_simulator()
    sim.add_item("Iron Sword", "weapons", base_price=150.0)
    sim.update_market(item_id, supply_delta=10, demand_delta=5)
    sim.create_currency(CurrencyType.GOLD, initial_amount=10000.0)
    sim.simulate_tick()
    snapshot = sim.get_economy_snapshot()
    imbalances = sim.detect_imbalances()
    suggestions = sim.get_balance_suggestions()
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

_time_module = time


# =============================================================================
# Enums
# =============================================================================


class CurrencyType(Enum):
    GOLD = "gold"
    SILVER = "silver"
    COPPER = "copper"
    CRYSTAL = "crystal"
    ESSENCE = "essence"
    REPUTATION = "reputation"


class MarketState(Enum):
    STABLE = "stable"
    VOLATILE = "volatile"
    BOOM = "boom"
    BUST = "bust"
    FROZEN = "frozen"


class TradeRouteStatus(Enum):
    ACTIVE = "active"
    DISRUPTED = "disrupted"
    EMBARGOED = "embargoed"
    PIRATED = "pirated"


class ProductionTier(Enum):
    RAW = "raw"
    REFINED = "refined"
    CRAFTED = "crafted"
    ENCHANTED = "enchanted"
    LEGENDARY = "legendary"


class ImbalanceType(Enum):
    INFLATION = "inflation"
    DEFLATION = "deflation"
    MONOPOLY = "monopoly"
    SCARCITY = "scarcity"
    GLUT = "glut"
    STAGNATION = "stagnation"


# =============================================================================
# Default exchange rate matrix (base rates between currencies)
# =============================================================================

_DEFAULT_EXCHANGE_RATES: Dict[str, Dict[str, float]] = {
    CurrencyType.GOLD.value: {
        CurrencyType.SILVER.value: 100.0,
        CurrencyType.COPPER.value: 10000.0,
        CurrencyType.CRYSTAL.value: 10.0,
        CurrencyType.ESSENCE.value: 1.0,
        CurrencyType.REPUTATION.value: 0.1,
    },
    CurrencyType.SILVER.value: {
        CurrencyType.GOLD.value: 0.01,
        CurrencyType.COPPER.value: 100.0,
        CurrencyType.CRYSTAL.value: 0.1,
        CurrencyType.ESSENCE.value: 0.01,
        CurrencyType.REPUTATION.value: 0.001,
    },
    CurrencyType.COPPER.value: {
        CurrencyType.GOLD.value: 0.0001,
        CurrencyType.SILVER.value: 0.01,
        CurrencyType.CRYSTAL.value: 0.001,
        CurrencyType.ESSENCE.value: 0.0001,
        CurrencyType.REPUTATION.value: 0.00001,
    },
    CurrencyType.CRYSTAL.value: {
        CurrencyType.GOLD.value: 0.1,
        CurrencyType.SILVER.value: 10.0,
        CurrencyType.COPPER.value: 1000.0,
        CurrencyType.ESSENCE.value: 0.1,
        CurrencyType.REPUTATION.value: 0.01,
    },
    CurrencyType.ESSENCE.value: {
        CurrencyType.GOLD.value: 1.0,
        CurrencyType.SILVER.value: 100.0,
        CurrencyType.COPPER.value: 10000.0,
        CurrencyType.CRYSTAL.value: 10.0,
        CurrencyType.REPUTATION.value: 0.1,
    },
    CurrencyType.REPUTATION.value: {
        CurrencyType.GOLD.value: 10.0,
        CurrencyType.SILVER.value: 1000.0,
        CurrencyType.COPPER.value: 100000.0,
        CurrencyType.CRYSTAL.value: 100.0,
        CurrencyType.ESSENCE.value: 10.0,
    },
}

# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class MarketItem:
    """Represents a tradable item in the game economy with market dynamics."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: str = ""
    base_price: float = 0.0
    current_price: float = 0.0
    supply: float = 0.0
    demand: float = 0.0
    price_history: List[float] = field(default_factory=list)
    elasticity: float = 1.0
    volatility: float = 0.05
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "base_price": self.base_price,
            "current_price": round(self.current_price, 2),
            "supply": round(self.supply, 2),
            "demand": round(self.demand, 2),
            "price_history": [round(p, 2) for p in self.price_history[-100:]],
            "elasticity": self.elasticity,
            "volatility": self.volatility,
            "last_updated": self.last_updated,
        }


@dataclass
class Currency:
    """Represents a currency type with its supply and exchange rate data."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    currency_type: CurrencyType = CurrencyType.GOLD
    amount: float = 0.0
    exchange_rates: Dict[str, float] = field(default_factory=dict)
    inflation_rate: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "currency_type": self.currency_type.value,
            "amount": round(self.amount, 2),
            "exchange_rates": {k: round(v, 4) for k, v in self.exchange_rates.items()},
            "inflation_rate": round(self.inflation_rate, 4),
            "created_at": self.created_at,
        }


@dataclass
class TradeRoute:
    """Represents a trade route between two regions with goods flow."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_region: str = ""
    target_region: str = ""
    goods: List[str] = field(default_factory=list)
    volume: float = 0.0
    status: TradeRouteStatus = TradeRouteStatus.ACTIVE
    tariff_rate: float = 0.0
    risk_level: float = 0.0
    established_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_region": self.source_region,
            "target_region": self.target_region,
            "goods": list(self.goods),
            "volume": round(self.volume, 2),
            "status": self.status.value,
            "tariff_rate": round(self.tariff_rate, 4),
            "risk_level": round(self.risk_level, 4),
            "established_at": self.established_at,
        }


@dataclass
class ProductionRecipe:
    """Represents a crafting recipe for transforming input resources into outputs."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    inputs: Dict[str, float] = field(default_factory=dict)
    outputs: Dict[str, float] = field(default_factory=dict)
    production_time: float = 1.0
    cost: float = 0.0
    tier: ProductionTier = ProductionTier.RAW
    required_skill: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "production_time": self.production_time,
            "cost": self.cost,
            "tier": self.tier.value,
            "required_skill": self.required_skill,
        }


@dataclass
class EconomySnapshot:
    """Captures the state of the entire economy at a point in time."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    gdp: float = 0.0
    gini_coefficient: float = 0.0
    inflation_rate: float = 0.0
    total_supply: float = 0.0
    total_demand: float = 0.0
    market_health: float = 1.0
    active_trades: int = 0
    imbalances: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "gdp": round(self.gdp, 2),
            "gini_coefficient": round(self.gini_coefficient, 4),
            "inflation_rate": round(self.inflation_rate, 4),
            "total_supply": round(self.total_supply, 2),
            "total_demand": round(self.total_demand, 2),
            "market_health": round(self.market_health, 4),
            "active_trades": self.active_trades,
            "imbalances": list(self.imbalances),
            "timestamp": self.timestamp,
        }


@dataclass
class ImbalanceReport:
    """Describes a detected economic imbalance with severity and suggested fix."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    imbalance_type: ImbalanceType = ImbalanceType.STAGNATION
    severity: float = 0.0
    affected_items: List[str] = field(default_factory=list)
    suggested_action: str = ""
    description: str = ""
    detected_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "imbalance_type": self.imbalance_type.value,
            "severity": round(self.severity, 4),
            "affected_items": list(self.affected_items),
            "suggested_action": self.suggested_action,
            "description": self.description,
            "detected_at": self.detected_at,
        }


# =============================================================================
# AgentEconomySimulator (Singleton)
# =============================================================================


class AgentEconomySimulator:
    """
    Game economy simulation and balancing engine.

    Provides a complete economic modeling system for game worlds including
    dynamic markets, multi-currency exchanges, trade networks, production
    chains, and automated imbalance detection. Runs tick-based simulations
    that advance supply/demand curves, compute price equilibrium, and
    generate balancing recommendations.

    Usage:
        sim = get_agent_economy_simulator()
        sim.add_item("Iron Sword", "weapons", base_price=150.0)
        sim.simulate_tick()
        snapshot = sim.get_economy_snapshot()
    """

    _instance: Optional["AgentEconomySimulator"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_TICK_INTERVAL = 1.0
    _MIN_PRICE_FLOOR = 0.01
    _MAX_PRICE_CEILING = 1_000_000_000.0
    _DEFAULT_INFLATION_TARGET = 0.02
    _DEFAULT_VOLATILITY = 0.05
    _MAX_PRICE_HISTORY = 500
    _GINI_SAMPLE_SIZE = 100
    _STAGNATION_THRESHOLD_TICKS = 20
    _INFLATION_SEVERITY_THRESHOLD = 0.15
    _DEFLATION_SEVERITY_THRESHOLD = -0.10
    _MONOPOLY_CONCENTRATION_THRESHOLD = 0.70
    _SCARCITY_RATIO_THRESHOLD = 0.10
    _GLUT_RATIO_THRESHOLD = 3.0

    def __new__(cls) -> "AgentEconomySimulator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentEconomySimulator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        # Market items indexed by item ID
        self._items: Dict[str, MarketItem] = {}

        # Currencies indexed by currency type value
        self._currencies: Dict[str, Currency] = {}

        # Trade routes
        self._trade_routes: List[TradeRoute] = []

        # Production recipes
        self._recipes: Dict[str, ProductionRecipe] = {}

        # Simulation state
        self._tick_count: int = 0
        self._snapshot_history: List[EconomySnapshot] = []
        self._imbalance_history: List[ImbalanceReport] = []

        # Wealth distribution simulation (for Gini coefficient)
        self._wealth_distribution: List[float] = [
            random.uniform(100.0, 10000.0) for _ in range(self._GINI_SAMPLE_SIZE)
        ]

        # Market-wide metrics
        self._global_inflation: float = 0.0
        self._market_health: float = 1.0
        self._total_gdp: float = 0.0

        # Stats tracking
        self._stats: Dict[str, Any] = {
            "total_ticks": 0,
            "total_items_added": 0,
            "total_trades": 0,
            "total_currencies_created": 0,
            "total_recipes_added": 0,
            "total_imbalances_detected": 0,
            "total_snapshots": 0,
        }

    # =========================================================================
    # Market Engine
    # =========================================================================

    def add_item(self,
                 name: str,
                 category: str,
                 base_price: float,
                 **kwargs: Any) -> MarketItem:
        """
        Add a new market item to the economy.

        Args:
            name: Display name of the item.
            category: Item category (e.g., 'weapons', 'potions', 'materials').
            base_price: The equilibrium/base price of the item.
            **kwargs: Optional overrides for supply, demand, elasticity, volatility.

        Returns:
            The newly created MarketItem.
        """
        initial_supply = kwargs.get("supply", base_price * random.uniform(5.0, 20.0))
        initial_demand = kwargs.get("demand", base_price * random.uniform(5.0, 20.0))
        elasticity = kwargs.get("elasticity", random.uniform(0.5, 2.0))
        volatility = kwargs.get("volatility", self._DEFAULT_VOLATILITY)

        item = MarketItem(
            name=name,
            category=category,
            base_price=base_price,
            current_price=base_price,
            supply=initial_supply,
            demand=initial_demand,
            price_history=[base_price],
            elasticity=elasticity,
            volatility=volatility,
        )
        self._items[item.id] = item
        self._stats["total_items_added"] += 1
        return item

    def update_market(self,
                      item_id: str,
                      supply_delta: float = 0.0,
                      demand_delta: float = 0.0) -> Optional[MarketItem]:
        """
        Update supply and/or demand for a market item, recalculating its price.

        Args:
            item_id: The ID of the market item to update.
            supply_delta: Change in supply (positive = more supply).
            demand_delta: Change in demand (positive = more demand).

        Returns:
            The updated MarketItem, or None if the item_id is not found.
        """
        item = self._items.get(item_id)
        if item is None:
            return None

        item.supply = max(0.0, item.supply + supply_delta)
        item.demand = max(0.0, item.demand + demand_delta)
        item.last_updated = _time_module.time()

        self._recompute_price(item)
        return item

    def get_price(self, item_id: str) -> Optional[float]:
        """
        Get the current market price of an item.

        Args:
            item_id: The ID of the market item.

        Returns:
            The current price as a float, or None if not found.
        """
        item = self._items.get(item_id)
        if item is None:
            return None
        return round(item.current_price, 2)

    def get_price_history(self,
                          item_id: str,
                          ticks: int = 100) -> List[float]:
        """
        Retrieve the price history for a market item.

        Args:
            item_id: The ID of the market item.
            ticks: Maximum number of historical price points to return.

        Returns:
            A list of historical prices (most recent last), or empty list if not found.
        """
        item = self._items.get(item_id)
        if item is None:
            return []
        return [round(p, 2) for p in item.price_history[-ticks:]]

    def get_market_state(self) -> MarketState:
        """
        Determine the overall market state based on volatility and health.

        Returns:
            The current MarketState enum value.
        """
        if self._market_health < 0.2:
            return MarketState.FROZEN
        if self._market_health < 0.4:
            return MarketState.BUST
        if self._global_inflation > 0.3:
            return MarketState.BOOM
        if self._global_inflation < -0.15:
            return MarketState.BUST

        # Compute average volatility across all items
        if self._items:
            avg_volatility = sum(
                abs(item.volatility) for item in self._items.values()
            ) / len(self._items)
            if avg_volatility > 0.15:
                return MarketState.VOLATILE

        return MarketState.STABLE

    def _recompute_price(self, item: MarketItem) -> None:
        """
        Recompute a market item's price based on supply, demand, and elasticity.

        Uses a supply-demand equilibrium model:
          price = base_price * (demand / max(supply, 1)) ^ (1 / elasticity)

        Args:
            item: The MarketItem to recompute.
        """
        if item.supply <= 0.0:
            item.supply = 0.01

        supply_demand_ratio = item.demand / max(item.supply, 0.001)
        exponent = 1.0 / max(item.elasticity, 0.01)
        equilibrium_price = item.base_price * (supply_demand_ratio ** exponent)

        # Apply volatility noise
        noise = random.uniform(-item.volatility, item.volatility)
        new_price = equilibrium_price * (1.0 + noise)

        # Clamp within reasonable bounds
        new_price = max(self._MIN_PRICE_FLOOR, min(self._MAX_PRICE_CEILING, new_price))
        item.current_price = round(new_price, 2)

        # Record price history
        item.price_history.append(item.current_price)
        if len(item.price_history) > self._MAX_PRICE_HISTORY:
            item.price_history = item.price_history[-self._MAX_PRICE_HISTORY:]

    # =========================================================================
    # Currency System
    # =========================================================================

    def create_currency(self,
                        currency_type: CurrencyType,
                        initial_amount: float,
                        **kwargs: Any) -> Currency:
        """
        Create a new currency pool in the economy.

        Args:
            currency_type: The type of currency to create.
                Accepts both CurrencyType enum and string values.
            initial_amount: Starting amount of this currency in circulation.
            **kwargs: Optional overrides for exchange_rates, inflation_rate.

        Returns:
            The newly created Currency.
        """
        # Accept both string and enum for currency_type
        if isinstance(currency_type, str):
            currency_type = CurrencyType(currency_type)
        ctype_value = currency_type.value

        exchange_rates = kwargs.get(
            "exchange_rates",
            dict(_DEFAULT_EXCHANGE_RATES.get(ctype_value, {})),
        )
        inflation_rate = kwargs.get("inflation_rate", 0.0)

        currency = Currency(
            currency_type=currency_type,
            amount=initial_amount,
            exchange_rates=exchange_rates,
            inflation_rate=inflation_rate,
        )
        self._currencies[ctype_value] = currency
        self._stats["total_currencies_created"] += 1
        return currency

    def exchange_currency(self,
                          from_type: CurrencyType,
                          to_type: CurrencyType,
                          amount: float) -> Optional[float]:
        """
        Exchange an amount from one currency type to another.

        Args:
            from_type: The source currency type.
            to_type: The target currency type.
            amount: The amount of source currency to convert.

        Returns:
            The converted amount in the target currency, or None if exchange
            is not possible (e.g., insufficient funds or missing currency).
        """
        from_key = from_type.value
        to_key = to_type.value

        if from_key == to_key:
            return amount

        from_currency = self._currencies.get(from_key)
        if from_currency is None:
            return None

        if from_currency.amount < amount:
            return None

        rate = from_currency.exchange_rates.get(to_key)
        if rate is None or rate <= 0.0:
            return None

        converted = amount * rate

        # Apply a small transaction spread (1% fee)
        converted *= 0.99

        from_currency.amount -= amount
        to_currency = self._currencies.get(to_key)
        if to_currency is not None:
            to_currency.amount += converted

        self._stats["total_trades"] += 1
        return round(converted, 2)

    def get_currency_amount(self, currency_type: CurrencyType) -> float:
        """
        Get the amount of a specific currency in circulation.

        Args:
            currency_type: The currency type to query.

        Returns:
            The amount in circulation, or 0.0 if not found.
        """
        currency = self._currencies.get(currency_type.value)
        if currency is None:
            return 0.0
        return currency.amount

    def adjust_inflation(self,
                         currency_type: CurrencyType,
                         delta: float) -> None:
        """
        Adjust the inflation rate for a specific currency.

        Args:
            currency_type: The currency type to adjust.
            delta: The change in inflation rate (positive = more inflation).
        """
        currency = self._currencies.get(currency_type.value)
        if currency is not None:
            currency.inflation_rate = max(-0.5, min(1.0, currency.inflation_rate + delta))

    # =========================================================================
    # Trade Network
    # =========================================================================

    def create_trade_route(self,
                           source: str,
                           target: str,
                           goods: List[str],
                           **kwargs: Any) -> TradeRoute:
        """
        Create a new trade route between two regions.

        Args:
            source: The source region name.
            target: The target/destination region name.
            goods: List of item names traded on this route.
            **kwargs: Optional overrides for volume, status, tariff_rate, risk_level.

        Returns:
            The newly created TradeRoute.
        """
        volume = kwargs.get("volume", random.uniform(10.0, 100.0))
        status_str = kwargs.get("status", "active")
        try:
            status = TradeRouteStatus(status_str)
        except ValueError:
            status = TradeRouteStatus.ACTIVE
        tariff_rate = kwargs.get("tariff_rate", random.uniform(0.0, 0.25))
        risk_level = kwargs.get("risk_level", random.uniform(0.0, 0.5))

        route = TradeRoute(
            source_region=source,
            target_region=target,
            goods=list(goods),
            volume=volume,
            status=status,
            tariff_rate=tariff_rate,
            risk_level=risk_level,
        )
        self._trade_routes.append(route)
        return route

    def update_trade_route_status(self,
                                   route_id: str,
                                   status: TradeRouteStatus) -> bool:
        """
        Update the status of an existing trade route.

        Args:
            route_id: The ID of the trade route to update.
            status: The new TradeRouteStatus.

        Returns:
            True if the route was found and updated, False otherwise.
        """
        for route in self._trade_routes:
            if route.id == route_id:
                route.status = status
                return True
        return False

    def get_active_trade_routes(self) -> List[TradeRoute]:
        """
        Get all currently active trade routes.

        Returns:
            A list of TradeRoute objects with ACTIVE status.
        """
        return [r for r in self._trade_routes if r.status == TradeRouteStatus.ACTIVE]

    # =========================================================================
    # Production Chain
    # =========================================================================

    def add_recipe(self,
                   name: str,
                   inputs: Dict[str, float],
                   outputs: Dict[str, float],
                   production_time: float = 1.0,
                   cost: float = 0.0,
                   tier: ProductionTier = ProductionTier.CRAFTED,
                   required_skill: float = 0.0,
                   **kwargs: Any) -> ProductionRecipe:
        """
        Add a production/crafting recipe to the economy.

        Args:
            name: Name of the recipe.
            inputs: Mapping of input item names to quantities required.
            outputs: Mapping of output item names to quantities produced.
            production_time: Time required to produce.
            cost: Base production cost.
            tier: Production tier.
            required_skill: Skill level required.
            **kwargs: Optional overrides.

        Returns:
            The newly created ProductionRecipe.
        """
        if isinstance(tier, str):
            try:
                tier = ProductionTier(tier)
            except ValueError:
                tier = ProductionTier.CRAFTED

        recipe = ProductionRecipe(
            name=name,
            inputs=dict(inputs),
            outputs=dict(outputs),
            production_time=production_time,
            cost=cost,
            tier=tier,
            required_skill=required_skill,
        )
        self._recipes[recipe.id] = recipe
        self._stats["total_recipes_added"] += 1
        return recipe

    def get_recipes_by_tier(self, tier: ProductionTier) -> List[ProductionRecipe]:
        """
        Get all recipes of a specific production tier.

        Args:
            tier: The ProductionTier to filter by.

        Returns:
            A list of matching ProductionRecipe objects.
        """
        return [r for r in self._recipes.values() if r.tier == tier]

    def compute_production_cost(self, recipe_id: str) -> Optional[float]:
        """
        Compute the total cost of producing a recipe based on current input prices.

        Args:
            recipe_id: The ID of the recipe to evaluate.

        Returns:
            The total production cost, or None if the recipe is not found.
        """
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return None

        total_cost = recipe.cost
        for input_name, input_qty in recipe.inputs.items():
            # Find matching item by name
            for item in self._items.values():
                if item.name.lower() == input_name.lower():
                    total_cost += item.current_price * input_qty
                    break

        return round(total_cost, 2)

    # =========================================================================
    # Simulation Tick
    # =========================================================================

    def simulate_tick(self) -> EconomySnapshot:
        """
        Advance the economy by one simulation tick.

        This method performs the following each tick:
          1. Updates all item prices based on supply/demand equilibrium.
          2. Applies random supply/demand shocks to simulate market activity.
          3. Updates currency inflation rates and applies inflation effects.
          4. Processes active trade routes (volume adjustments).
          5. Updates wealth distribution and computes Gini coefficient.
          6. Computes GDP, market health, and other macroeconomic indicators.
          7. Generates an EconomySnapshot.

        Returns:
            An EconomySnapshot representing the state after this tick.
        """
        self._tick_count += 1
        self._stats["total_ticks"] += 1

        # ---- 1. Update item prices and apply random market shocks ----
        for item in self._items.values():
            # Random supply/demand fluctuation
            supply_shock = random.uniform(-0.1, 0.15) * item.supply * 0.05
            demand_shock = random.uniform(-0.1, 0.15) * item.demand * 0.05

            item.supply = max(0.0, item.supply + supply_shock)
            item.demand = max(0.0, item.demand + demand_shock)
            item.last_updated = _time_module.time()

            self._recompute_price(item)

        # ---- 2. Update currency inflation ----
        total_currency_value = 0.0
        for currency in self._currencies.values():
            # Inflation erodes or grows the effective money supply
            inflation_effect = currency.amount * currency.inflation_rate
            currency.amount += inflation_effect
            # Natural mean-reversion toward 2% target
            currency.inflation_rate += random.uniform(-0.005, 0.005)
            currency.inflation_rate *= 0.98
            currency.inflation_rate += (self._DEFAULT_INFLATION_TARGET - currency.inflation_rate) * 0.01
            total_currency_value += currency.amount

        # ---- 3. Compute global inflation rate ----
        if self._items:
            price_changes: List[float] = []
            for item in self._items.values():
                if len(item.price_history) >= 2:
                    prev = item.price_history[-2]
                    curr = item.price_history[-1]
                    if prev > 0:
                        price_changes.append((curr - prev) / prev)
            if price_changes:
                self._global_inflation = sum(price_changes) / len(price_changes)

        # ---- 4. Process active trade routes ----
        for route in self._trade_routes:
            if route.status == TradeRouteStatus.ACTIVE:
                # Volume fluctuates based on risk
                volume_change = random.uniform(-0.1, 0.1) * route.volume
                if route.risk_level > 0.5:
                    volume_change -= route.volume * random.uniform(0.0, route.risk_level * 0.1)
                route.volume = max(0.0, route.volume + volume_change)

                # Random route disruption
                if random.random() < route.risk_level * 0.05:
                    route.status = TradeRouteStatus.DISRUPTED

        # ---- 5. Update wealth distribution ----
        for i in range(len(self._wealth_distribution)):
            change_pct = random.uniform(-0.05, 0.08)
            self._wealth_distribution[i] = max(
                1.0, self._wealth_distribution[i] * (1.0 + change_pct)
            )

        gini = self._compute_gini(self._wealth_distribution)

        # ---- 6. Compute GDP and market health ----
        total_supply = sum(item.supply for item in self._items.values())
        total_demand = sum(item.demand for item in self._items.values())
        self._total_gdp = sum(
            item.current_price * min(item.supply, item.demand)
            for item in self._items.values()
        )

        # Market health: composite of stability, diversity, and activity
        supply_demand_balance = 1.0 - abs(total_supply - total_demand) / max(
            total_supply + total_demand, 1.0
        )
        item_diversity = min(1.0, len(self._items) / 20.0)
        trade_activity = min(1.0, len(self.get_active_trade_routes()) / 10.0)
        inflation_health = 1.0 - min(1.0, abs(self._global_inflation) / 0.3)

        self._market_health = (
            supply_demand_balance * 0.35
            + item_diversity * 0.25
            + trade_activity * 0.20
            + inflation_health * 0.20
        )

        # ---- 7. Detect imbalances and generate snapshot ----
        imbalances = self._detect_current_imbalances()
        imbalance_types = [ib.imbalance_type.value for ib in imbalances]

        snapshot = EconomySnapshot(
            gdp=self._total_gdp,
            gini_coefficient=gini,
            inflation_rate=self._global_inflation,
            total_supply=total_supply,
            total_demand=total_demand,
            market_health=self._market_health,
            active_trades=len(self.get_active_trade_routes()),
            imbalances=imbalance_types,
        )

        self._snapshot_history.append(snapshot)
        self._stats["total_snapshots"] += 1

        if len(self._snapshot_history) > self._MAX_PRICE_HISTORY:
            self._snapshot_history = self._snapshot_history[-self._MAX_PRICE_HISTORY:]

        return snapshot

    def _detect_current_imbalances(self) -> List[ImbalanceReport]:
        """
        Detect current economic imbalances across all items and currencies.

        Returns:
            A list of ImbalanceReport objects describing detected issues.
        """
        reports: List[ImbalanceReport] = []

        # ---- Inflation detection ----
        if self._global_inflation > self._INFLATION_SEVERITY_THRESHOLD:
            severity = min(1.0, self._global_inflation / 0.5)
            affected = []
            for item in self._items.values():
                if len(item.price_history) >= 2:
                    recent_change = (item.price_history[-1] - item.price_history[0]) / max(
                        item.price_history[0], 0.01
                    )
                    if recent_change > self._INFLATION_SEVERITY_THRESHOLD:
                        affected.append(item.name)
            reports.append(ImbalanceReport(
                imbalance_type=ImbalanceType.INFLATION,
                severity=round(severity, 4),
                affected_items=affected[:10],
                suggested_action=(
                    "Reduce currency faucets by 20-30% or increase sink costs. "
                    "Consider adding gold sinks for high-level players."
                ),
                description=(
                    f"Prices rising at {self._global_inflation*100:.1f}% per tick. "
                    f"{len(affected)} items showing significant price increases."
                ),
            ))

        # ---- Deflation detection ----
        if self._global_inflation < self._DEFLATION_SEVERITY_THRESHOLD:
            severity = min(1.0, abs(self._global_inflation) / 0.3)
            affected = []
            for item in self._items.values():
                if len(item.price_history) >= 2:
                    recent_change = (item.price_history[-1] - item.price_history[0]) / max(
                        item.price_history[0], 0.01
                    )
                    if recent_change < self._DEFLATION_SEVERITY_THRESHOLD:
                        affected.append(item.name)
            reports.append(ImbalanceReport(
                imbalance_type=ImbalanceType.DEFLATION,
                severity=round(severity, 4),
                affected_items=affected[:10],
                suggested_action=(
                    "Increase currency rewards or reduce item drop rates. "
                    "Introduce new spending incentives for players."
                ),
                description=(
                    f"Prices falling at {abs(self._global_inflation)*100:.1f}% per tick. "
                    f"Currency may be leaving circulation too quickly."
                ),
            ))

        # ---- Monopoly detection (single item dominates market) ----
        if self._items:
            total_value = sum(
                item.current_price * item.supply for item in self._items.values()
            )
            if total_value > 0:
                for item in self._items.values():
                    item_share = (item.current_price * item.supply) / total_value
                    if item_share > self._MONOPOLY_CONCENTRATION_THRESHOLD:
                        reports.append(ImbalanceReport(
                            imbalance_type=ImbalanceType.MONOPOLY,
                            severity=round(item_share, 4),
                            affected_items=[item.name],
                            suggested_action=(
                                f"Introduce competing items in the '{item.category}' category. "
                                f"Increase supply diversity or add alternative sources."
                            ),
                            description=(
                                f"'{item.name}' controls {item_share*100:.1f}% of total market value. "
                                f"Market concentration is dangerously high."
                            ),
                        ))

        # ---- Scarcity detection (supply far below demand) ----
        for item in self._items.values():
            if item.demand > 0 and item.supply / item.demand < self._SCARCITY_RATIO_THRESHOLD:
                reports.append(ImbalanceReport(
                    imbalance_type=ImbalanceType.SCARCITY,
                    severity=round(1.0 - item.supply / max(item.demand, 0.01), 4),
                    affected_items=[item.name],
                    suggested_action=(
                        f"Increase drop rates or spawn frequency for '{item.name}'. "
                        f"Consider adding alternative sources or crafting recipes."
                    ),
                    description=(
                        f"'{item.name}' supply ({item.supply:.1f}) is critically low "
                        f"relative to demand ({item.demand:.1f})."
                    ),
                ))

        # ---- Glut detection (supply far exceeds demand) ----
        for item in self._items.values():
            if item.demand > 0 and item.supply / item.demand > self._GLUT_RATIO_THRESHOLD:
                reports.append(ImbalanceReport(
                    imbalance_type=ImbalanceType.GLUT,
                    severity=round(min(1.0, item.supply / (item.demand * 5.0)), 4),
                    affected_items=[item.name],
                    suggested_action=(
                        f"Reduce drop rates for '{item.name}' or introduce new "
                        f"consumption sinks (crafting, upgrades, quests)."
                    ),
                    description=(
                        f"'{item.name}' supply ({item.supply:.1f}) far exceeds "
                        f"demand ({item.demand:.1f}), causing price collapse."
                    ),
                ))

        # ---- Stagnation detection (no price movement for many ticks) ----
        for item in self._items.values():
            if len(item.price_history) >= self._STAGNATION_THRESHOLD_TICKS:
                recent = item.price_history[-self._STAGNATION_THRESHOLD_TICKS:]
                if len(recent) >= 2:
                    max_p = max(recent)
                    min_p = min(recent)
                    avg_p = sum(recent) / len(recent)
                    if avg_p > 0 and (max_p - min_p) / avg_p < 0.01:
                        reports.append(ImbalanceReport(
                            imbalance_type=ImbalanceType.STAGNATION,
                            severity=0.5,
                            affected_items=[item.name],
                            suggested_action=(
                                f"Introduce market events or adjust supply/demand for "
                                f"'{item.name}' to stimulate trading activity."
                            ),
                            description=(
                                f"'{item.name}' price has been stagnant for "
                                f"{self._STAGNATION_THRESHOLD_TICKS}+ ticks."
                            ),
                        ))

        # Store imbalance reports
        for report in reports:
            self._imbalance_history.append(report)
        self._stats["total_imbalances_detected"] += len(reports)

        return reports

    # =========================================================================
    # Economy Metrics
    # =========================================================================

    def get_economy_snapshot(self) -> EconomySnapshot:
        """
        Get the current state of the economy without advancing a tick.

        Returns:
            An EconomySnapshot representing the current economy state.
        """
        total_supply = sum(item.supply for item in self._items.values())
        total_demand = sum(item.demand for item in self._items.values())
        gini = self._compute_gini(self._wealth_distribution)

        return EconomySnapshot(
            gdp=self._total_gdp,
            gini_coefficient=gini,
            inflation_rate=self._global_inflation,
            total_supply=total_supply,
            total_demand=total_demand,
            market_health=self._market_health,
            active_trades=len(self.get_active_trade_routes()),
            imbalances=[],
        )

    def detect_imbalances(self) -> List[ImbalanceReport]:
        """
        Run a full imbalance detection pass on the current economy state.

        Returns:
            A list of ImbalanceReport objects describing detected issues.
        """
        return self._detect_current_imbalances()

    def get_balance_suggestions(self) -> List[Dict[str, Any]]:
        """
        Get balancing suggestions for all detected economic imbalances.

        Returns:
            A list of dictionaries, each containing imbalance type, severity,
            affected items, and suggested actions.
        """
        imbalances = self._detect_current_imbalances()
        suggestions: List[Dict[str, Any]] = []
        for report in imbalances:
            suggestions.append({
                "type": report.imbalance_type.value,
                "severity": report.severity,
                "affected_items": list(report.affected_items),
                "suggested_action": report.suggested_action,
                "description": report.description,
            })
        return suggestions

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the economy simulation.

        Returns:
            A dictionary containing counts, metrics, and state information.
        """
        return {
            "total_ticks": self._stats["total_ticks"],
            "total_items": len(self._items),
            "total_items_added": self._stats["total_items_added"],
            "total_currencies": len(self._currencies),
            "total_currencies_created": self._stats["total_currencies_created"],
            "total_trade_routes": len(self._trade_routes),
            "active_trade_routes": len(self.get_active_trade_routes()),
            "total_trades": self._stats["total_trades"],
            "total_recipes": len(self._recipes),
            "total_recipes_added": self._stats["total_recipes_added"],
            "total_imbalances_detected": self._stats["total_imbalances_detected"],
            "total_snapshots": self._stats["total_snapshots"],
            "current_market_state": self.get_market_state().value,
            "global_inflation": round(self._global_inflation, 4),
            "market_health": round(self._market_health, 4),
            "gdp": round(self._total_gdp, 2),
            "gini_coefficient": round(self._compute_gini(self._wealth_distribution), 4),
            "snapshot_history_size": len(self._snapshot_history),
            "imbalance_history_size": len(self._imbalance_history),
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the entire economy simulator state to a dictionary.

        Returns:
            A comprehensive dictionary representation of all economy data.
        """
        return {
            "tick_count": self._tick_count,
            "items": [item.to_dict() for item in self._items.values()],
            "currencies": [c.to_dict() for c in self._currencies.values()],
            "trade_routes": [r.to_dict() for r in self._trade_routes],
            "recipes": [r.to_dict() for r in self._recipes.values()],
            "global_inflation": round(self._global_inflation, 4),
            "market_health": round(self._market_health, 4),
            "total_gdp": round(self._total_gdp, 2),
            "gini_coefficient": round(self._compute_gini(self._wealth_distribution), 4),
            "market_state": self.get_market_state().value,
            "snapshot_history": [s.to_dict() for s in self._snapshot_history[-50:]],
            "imbalance_history": [ir.to_dict() for ir in self._imbalance_history[-50:]],
            "stats": self.get_stats(),
        }

    # =========================================================================
    # Helpers
    # =========================================================================

    def reset(self) -> None:
        """Reset the entire economy simulator to its initial state."""
        self._items.clear()
        self._currencies.clear()
        self._trade_routes.clear()
        self._recipes.clear()
        self._tick_count = 0
        self._snapshot_history.clear()
        self._imbalance_history.clear()
        self._wealth_distribution = [
            random.uniform(100.0, 10000.0) for _ in range(self._GINI_SAMPLE_SIZE)
        ]
        self._global_inflation = 0.0
        self._market_health = 1.0
        self._total_gdp = 0.0
        self._stats = {
            "total_ticks": 0,
            "total_items_added": 0,
            "total_trades": 0,
            "total_currencies_created": 0,
            "total_recipes_added": 0,
            "total_imbalances_detected": 0,
            "total_snapshots": 0,
        }

    @staticmethod
    def _compute_gini(wealth: List[float]) -> float:
        """
        Compute the Gini coefficient for a wealth distribution.

        The Gini coefficient measures inequality: 0 = perfect equality,
        1 = perfect inequality (one person has everything).

        Args:
            wealth: List of wealth values for each individual.

        Returns:
            The Gini coefficient as a float between 0 and 1.
        """
        if not wealth or len(wealth) < 2:
            return 0.0

        sorted_wealth = sorted(wealth)
        n = len(sorted_wealth)
        total = sum(sorted_wealth)

        if total <= 0:
            return 0.0

        # Gini = (2 * sum(i * w_i) / (n * sum(w_i))) - (n + 1) / n
        numerator = sum((i + 1) * w for i, w in enumerate(sorted_wealth))
        gini = (2.0 * numerator) / (n * total) - (n + 1.0) / n
        return round(max(0.0, min(1.0, gini)), 4)


# =============================================================================
# Module-level accessor
# =============================================================================


def get_agent_economy_simulator() -> AgentEconomySimulator:
    """Get or create the singleton AgentEconomySimulator instance."""
    return AgentEconomySimulator.get_instance()