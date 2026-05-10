"""
SparkLabs Engine - Economy System

Comprehensive in-game economic simulation with dynamic market
pricing, currency management, trading mechanics, resource
flow tracking, and inflation control. Models supply-demand
equilibrium with configurable elasticity curves.

Architecture:
  EconomySystem
    |-- CurrencyManager (multi-currency wallet and exchange)
    |-- MarketPricing (supply-demand-driven price fluctuation)
    |-- TradeNetwork (vendor inventory and player-to-player trading)
    |-- ResourceTracker (production, consumption, and scarcity)
    |-- InflationController (money supply and value stabilization)

Currency Types:
  - GOLD, SILVER, COPPER (standard)
  - CRYSTAL, TOKEN, REPUTATION (special)
  - Custom currencies with exchange rates
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CurrencyType(Enum):
    GOLD = "gold"
    SILVER = "silver"
    COPPER = "copper"
    CRYSTAL = "crystal"
    TOKEN = "token"
    REPUTATION = "reputation"


class TradeType(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class CurrencyDefinition:
    currency_type: CurrencyType
    name: str = ""
    base_exchange_rate: float = 1.0
    is_premium: bool = False
    icon_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.currency_type.value,
            "name": self.name,
            "exchange_rate": self.base_exchange_rate,
            "is_premium": self.is_premium,
        }


@dataclass
class MarketItem:
    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: str = ""
    base_price: float = 0.0
    current_price: float = 0.0
    price_elasticity: float = 0.5
    supply: int = 100
    demand: int = 100
    min_price: float = 0.0
    max_price: float = float("inf")
    transaction_count: int = 0
    last_transaction_time: float = 0.0
    price_history: List[float] = field(default_factory=list)

    def __post_init__(self):
        if self.current_price == 0.0:
            self.current_price = self.base_price


@dataclass
class Wallet:
    owner_id: str
    balances: Dict[CurrencyType, float] = field(default_factory=dict)
    transaction_history: List[Dict[str, Any]] = field(default_factory=list)
    total_earned: Dict[CurrencyType, float] = field(default_factory=dict)
    total_spent: Dict[CurrencyType, float] = field(default_factory=dict)


@dataclass
class Transaction:
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    buyer_id: str = ""
    seller_id: str = ""
    trade_type: TradeType = TradeType.BUY
    item_id: str = ""
    item_name: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    currency_type: CurrencyType = CurrencyType.GOLD
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.total_price == 0.0 and self.unit_price > 0:
            self.total_price = self.unit_price * self.quantity


class EconomySystem:
    _instance: Optional[EconomySystem] = None

    DEFAULT_CURRENCIES: List[CurrencyDefinition] = [
        CurrencyDefinition(CurrencyType.COPPER, "Copper", 1.0),
        CurrencyDefinition(CurrencyType.SILVER, "Silver", 100.0),
        CurrencyDefinition(CurrencyType.GOLD, "Gold", 10000.0),
        CurrencyDefinition(CurrencyType.CRYSTAL, "Crystal", 50000.0, True),
        CurrencyDefinition(CurrencyType.TOKEN, "Token", 1.0),
        CurrencyDefinition(CurrencyType.REPUTATION, "Reputation", 1.0),
    ]

    def __init__(self):
        self._currencies: Dict[CurrencyType, CurrencyDefinition] = {}
        self._market: Dict[str, MarketItem] = {}
        self._wallets: Dict[str, Wallet] = {}
        self._transactions: List[Transaction] = []
        self._global_inflation: float = 0.0
        self._total_money_supply: float = 0.0

        for currency_def in self.DEFAULT_CURRENCIES:
            self._currencies[currency_def.currency_type] = currency_def

    @classmethod
    def get_instance(cls) -> EconomySystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_wallet(self, owner_id: str, initial_balance: float = 0.0) -> Wallet:
        wallet = Wallet(
            owner_id=owner_id,
            balances={CurrencyType.GOLD: initial_balance},
            total_earned={CurrencyType.GOLD: 0.0},
            total_spent={CurrencyType.GOLD: 0.0},
        )
        self._wallets[owner_id] = wallet
        return wallet

    def get_balance(self, owner_id: str, currency: CurrencyType = CurrencyType.GOLD) -> float:
        wallet = self._wallets.get(owner_id)
        if wallet is None:
            return 0.0
        return wallet.balances.get(currency, 0.0)

    def add_currency(
        self, owner_id: str, amount: float, currency: CurrencyType = CurrencyType.GOLD
    ) -> float:
        wallet = self._wallets.get(owner_id)
        if wallet is None:
            wallet = self.create_wallet(owner_id)
        wallet.balances[currency] = wallet.balances.get(currency, 0.0) + amount
        wallet.total_earned[currency] = wallet.total_earned.get(currency, 0.0) + amount
        self._total_money_supply += amount
        return wallet.balances[currency]

    def remove_currency(
        self, owner_id: str, amount: float, currency: CurrencyType = CurrencyType.GOLD
    ) -> Tuple[bool, float]:
        wallet = self._wallets.get(owner_id)
        if wallet is None:
            return False, 0.0
        current = wallet.balances.get(currency, 0.0)
        if current < amount:
            return False, current
        wallet.balances[currency] = current - amount
        wallet.total_spent[currency] = wallet.total_spent.get(currency, 0.0) + amount
        self._total_money_supply -= amount
        return True, wallet.balances[currency]

    def register_market_item(self, item: MarketItem) -> str:
        self._market[item.item_id] = item
        return item.item_id

    def get_market_price(self, item_id: str) -> float:
        item = self._market.get(item_id)
        if item is None:
            return 0.0
        return item.current_price

    def update_market(self, delta_time: float = 1.0):
        for item in self._market.values():
            demand_ratio = item.demand / max(1, item.supply)
            target_price = item.base_price * demand_ratio

            adjustment = (target_price - item.current_price) * item.price_elasticity * delta_time
            item.current_price += adjustment
            item.current_price = max(item.min_price, min(item.max_price, item.current_price))

            item.supply = int(item.supply * (1.0 + random.uniform(-0.05, 0.1)))
            item.demand = int(item.demand * (1.0 + random.uniform(-0.05, 0.1)))

    def execute_trade(
        self,
        buyer_id: str,
        seller_id: str,
        item_id: str,
        quantity: int = 1,
        currency: CurrencyType = CurrencyType.GOLD,
    ) -> Optional[Transaction]:
        item = self._market.get(item_id)
        if item is None:
            return None

        if seller_id != "market" and seller_id not in self._wallets:
            return None

        total = item.current_price * quantity
        success, remaining = self.remove_currency(buyer_id, total, currency)
        if not success:
            return None

        if seller_id != "market":
            self.add_currency(seller_id, total, currency)

        item.transaction_count += quantity
        item.last_transaction_time = time.time()
        item.price_history.append(item.current_price)
        if len(item.price_history) > 100:
            item.price_history = item.price_history[-100]

        item.demand += quantity

        transaction = Transaction(
            buyer_id=buyer_id,
            seller_id=seller_id,
            trade_type=TradeType.BUY,
            item_id=item_id,
            item_name=item.name,
            quantity=quantity,
            unit_price=item.current_price,
            total_price=total,
            currency_type=currency,
        )
        self._transactions.append(transaction)

        wallet = self._wallets.get(buyer_id)
        if wallet:
            wallet.transaction_history.append({
                "transaction_id": transaction.transaction_id,
                "item_name": item.name,
                "quantity": quantity,
                "total_price": total,
                "timestamp": transaction.timestamp,
            })

        return transaction

    def convert_currency(
        self, owner_id: str, amount: float, from_currency: CurrencyType, to_currency: CurrencyType
    ) -> Tuple[bool, float]:
        from_def = self._currencies.get(from_currency)
        to_def = self._currencies.get(to_currency)
        if from_def is None or to_def is None:
            return False, 0.0

        success, _ = self.remove_currency(owner_id, amount, from_currency)
        if not success:
            return False, 0.0

        converted = amount * from_def.base_exchange_rate / to_def.base_exchange_rate
        fee_rate = 0.02 if not from_def.is_premium and not to_def.is_premium else 0.0
        converted *= (1.0 - fee_rate)

        self.add_currency(owner_id, converted, to_currency)
        return True, converted

    def get_wallet_summary(self, owner_id: str) -> Optional[Dict[str, Any]]:
        wallet = self._wallets.get(owner_id)
        if wallet is None:
            return None
        return {
            "owner_id": wallet.owner_id,
            "balances": {k.value: v for k, v in wallet.balances.items()},
            "total_earned": {k.value: v for k, v in wallet.total_earned.items()},
            "total_spent": {k.value: v for k, v in wallet.total_spent.items()},
            "recent_transactions": wallet.transaction_history[-10:],
        }

    def get_market_summary(self) -> Dict[str, Any]:
        items = {}
        for item in self._market.values():
            trend = "stable"
            if len(item.price_history) >= 2:
                if item.price_history[-1] > item.price_history[-2] * 1.05:
                    trend = "rising"
                elif item.price_history[-1] < item.price_history[-2] * 0.95:
                    trend = "falling"
            items[item.item_id] = {
                "name": item.name,
                "price": round(item.current_price, 2),
                "base_price": round(item.base_price, 2),
                "trend": trend,
                "supply": item.supply,
                "demand": item.demand,
            }
        return {
            "total_listings": len(self._market),
            "items": items,
            "recent_transactions": len(self._transactions[-20:]),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "wallets": len(self._wallets),
            "market_items": len(self._market),
            "total_transactions": len(self._transactions),
            "currencies": [c.value for c in self._currencies],
            "total_money_supply": round(self._total_money_supply, 2),
            "inflation_rate": round(self._global_inflation, 4),
        }


def get_economy_system() -> EconomySystem:
    return EconomySystem.get_instance()