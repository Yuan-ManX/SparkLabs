"""
SparkLabs Agent - Monetization Designer

Comprehensive game monetization design intelligence that creates
balanced revenue strategies, configures optimal pricing structures,
maintains healthy virtual economies, and audits monetization fairness.
Supports multiple revenue models across diverse game genres with
real-time forecasting and conversion funnel optimization.

Architecture:
  AgentMonetizationDesigner (Singleton)
    |-- RevenueModel (monetization strategy blueprint)
    |-- PricingStrategy (price points and regional adjustments)
    |-- EconomyBalance (currency flows and wealth distribution)
    |-- IAPDesign (in-app purchase catalog with tiered offerings)
    |-- MonetizationAudit (fairness and compliance evaluation)

Revenue Model Types:
  PREMIUM, FREEMIUM, SUBSCRIPTION, BATTLE_PASS, COSMETIC, DLC

Currency Types:
  SOFT, HARD, PREMIUM, SEASONAL, GUILD, EVENT, REPUTATION

Monetization Tiers:
  BUDGET, STANDARD, DELUXE, ULTIMATE, WHALE

Supported Game Genres:
  RPG, FPS, MOBA, STRATEGY, CASUAL, SIMULATION, SPORTS, BATTLE_ROYALE
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RevenueModelType(Enum):
    PREMIUM = "premium"
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    BATTLE_PASS = "battle_pass"
    COSMETIC = "cosmetic"
    DLC = "dlc"


class CurrencyType(Enum):
    SOFT = "soft"
    HARD = "hard"
    PREMIUM = "premium"
    SEASONAL = "seasonal"
    GUILD = "guild"
    EVENT = "event"
    REPUTATION = "reputation"


class MonetizationTier(Enum):
    BUDGET = "budget"
    STANDARD = "standard"
    DELUXE = "deluxe"
    ULTIMATE = "ultimate"
    WHALE = "whale"


_GENRE_REVENUE_TEMPLATES: Dict[str, List[str]] = {
    "rpg": [
        RevenueModelType.PREMIUM.value,
        RevenueModelType.DLC.value,
        RevenueModelType.COSMETIC.value,
    ],
    "fps": [
        RevenueModelType.PREMIUM.value,
        RevenueModelType.BATTLE_PASS.value,
        RevenueModelType.COSMETIC.value,
    ],
    "moba": [
        RevenueModelType.FREEMIUM.value,
        RevenueModelType.BATTLE_PASS.value,
        RevenueModelType.COSMETIC.value,
    ],
    "strategy": [
        RevenueModelType.PREMIUM.value,
        RevenueModelType.DLC.value,
        RevenueModelType.SUBSCRIPTION.value,
    ],
    "casual": [
        RevenueModelType.FREEMIUM.value,
        RevenueModelType.SUBSCRIPTION.value,
    ],
    "simulation": [
        RevenueModelType.PREMIUM.value,
        RevenueModelType.DLC.value,
    ],
    "sports": [
        RevenueModelType.PREMIUM.value,
        RevenueModelType.BATTLE_PASS.value,
        RevenueModelType.COSMETIC.value,
    ],
    "battle_royale": [
        RevenueModelType.FREEMIUM.value,
        RevenueModelType.BATTLE_PASS.value,
        RevenueModelType.COSMETIC.value,
    ],
}

_GENRE_PRICING_BASELINES: Dict[str, Dict[str, float]] = {
    "rpg": {"base_price": 59.99, "dlc_price": 19.99, "battle_pass": 9.99, "subscription_monthly": 14.99},
    "fps": {"base_price": 69.99, "dlc_price": 14.99, "battle_pass": 9.99, "subscription_monthly": 9.99},
    "moba": {"base_price": 0.0, "dlc_price": 0.0, "battle_pass": 9.99, "subscription_monthly": 0.0},
    "strategy": {"base_price": 49.99, "dlc_price": 19.99, "battle_pass": 0.0, "subscription_monthly": 4.99},
    "casual": {"base_price": 0.0, "dlc_price": 0.0, "battle_pass": 4.99, "subscription_monthly": 6.99},
    "simulation": {"base_price": 39.99, "dlc_price": 14.99, "battle_pass": 0.0, "subscription_monthly": 0.0},
    "sports": {"base_price": 69.99, "dlc_price": 0.0, "battle_pass": 9.99, "subscription_monthly": 0.0},
    "battle_royale": {"base_price": 0.0, "dlc_price": 0.0, "battle_pass": 9.99, "subscription_monthly": 0.0},
}

_REGIONAL_MULTIPLIERS: Dict[str, float] = {
    "US": 1.00, "EU": 1.08, "UK": 1.05, "JP": 1.12,
    "CN": 0.65, "BR": 0.55, "IN": 0.40, "RU": 0.50,
    "KR": 0.95, "AU": 1.02, "CA": 0.98, "MX": 0.50,
    "SEA": 0.45, "ME": 0.65, "AF": 0.35, "LATAM": 0.48,
}

_DEFAULT_CONVERSION_FUNNEL: Dict[str, float] = {
    "impression_to_install": 0.025,
    "install_to_tutorial_complete": 0.60,
    "tutorial_to_first_session": 0.80,
    "first_session_to_engaged": 0.40,
    "engaged_to_first_purchase": 0.08,
    "first_purchase_to_repeat": 0.25,
    "repeat_to_subscriber": 0.10,
}

_CURRENCY_SINK_TYPES: List[str] = [
    "consumable_purchase", "cosmetic_unlock", "gear_upgrade",
    "speed_up_timer", "reroll_stat", "inventory_expansion",
    "guild_donation", "event_entry_fee",
]

_CURRENCY_SOURCE_TYPES: List[str] = [
    "daily_login", "quest_completion", "achievement_unlock",
    "season_reward", "event_participation", "referral_bonus",
    "ad_reward", "compensation_grant",
]

_WHALE_THRESHOLD_MONTHLY = 500.0
_DOLPHIN_THRESHOLD_MONTHLY = 50.0
_MINNOW_THRESHOLD_MONTHLY = 5.0

_FAIRNESS_WEIGHTS: Dict[str, float] = {
    "pay_to_win_ratio": 0.30,
    "progression_gating": 0.20,
    "cosmetic_exclusivity": 0.10,
    "price_transparency": 0.15,
    "refund_policy": 0.10,
    "predatory_mechanics": 0.15,
}


@dataclass
class RevenueModel:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    model_type: str = RevenueModelType.PREMIUM.value
    genre: str = ""
    pricing_tiers: List[Dict[str, Any]] = field(default_factory=list)
    primary_currency: str = CurrencyType.SOFT.value
    secondary_currencies: List[str] = field(default_factory=list)
    estimated_arpu: float = 0.0
    conversion_rate_target: float = 0.05
    player_lifetime_value: float = 0.0
    market_positioning: str = "standard"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_type": self.model_type,
            "genre": self.genre,
            "pricing_tiers": [dict(t) for t in self.pricing_tiers],
            "primary_currency": self.primary_currency,
            "secondary_currencies": list(self.secondary_currencies),
            "estimated_arpu": round(self.estimated_arpu, 2),
            "conversion_rate_target": round(self.conversion_rate_target, 4),
            "player_lifetime_value": round(self.player_lifetime_value, 2),
            "market_positioning": self.market_positioning,
            "created_at": self.created_at,
        }


@dataclass
class PricingStrategy:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    revenue_model_id: str = ""
    base_price_usd: float = 0.0
    regional_prices: Dict[str, float] = field(default_factory=dict)
    discount_schedule: List[Dict[str, Any]] = field(default_factory=list)
    bundle_configurations: List[Dict[str, Any]] = field(default_factory=list)
    price_anchor: float = 0.0
    psychological_pricing_enabled: bool = True
    dynamic_pricing_enabled: bool = False
    min_price: float = 0.99
    max_price: float = 99.99
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "revenue_model_id": self.revenue_model_id,
            "base_price_usd": round(self.base_price_usd, 2),
            "regional_prices": {k: round(v, 2) for k, v in self.regional_prices.items()},
            "discount_schedule": [dict(d) for d in self.discount_schedule],
            "bundle_configurations": [dict(b) for b in self.bundle_configurations],
            "price_anchor": round(self.price_anchor, 2),
            "psychological_pricing_enabled": self.psychological_pricing_enabled,
            "dynamic_pricing_enabled": self.dynamic_pricing_enabled,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "generated_at": self.generated_at,
        }


@dataclass
class EconomyBalance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_id: str = ""
    currency_pools: Dict[str, float] = field(default_factory=dict)
    sink_source_ratios: Dict[str, float] = field(default_factory=dict)
    inflation_rate: float = 0.0
    inflation_trend: List[float] = field(default_factory=list)
    wealth_distribution: Dict[str, float] = field(default_factory=dict)
    gini_coefficient: float = 0.0
    daily_active_volume: float = 0.0
    economy_health_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    analyzed_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "currency_pools": {k: round(v, 2) for k, v in self.currency_pools.items()},
            "sink_source_ratios": {k: round(v, 4) for k, v in self.sink_source_ratios.items()},
            "inflation_rate": round(self.inflation_rate, 4),
            "inflation_trend": [round(v, 4) for v in self.inflation_trend],
            "wealth_distribution": {k: round(v, 2) for k, v in self.wealth_distribution.items()},
            "gini_coefficient": round(self.gini_coefficient, 4),
            "daily_active_volume": round(self.daily_active_volume, 2),
            "economy_health_score": round(self.economy_health_score, 2),
            "recommendations": list(self.recommendations),
            "analyzed_at": self.analyzed_at,
        }


@dataclass
class IAPDesign:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_id: str = ""
    revenue_model_id: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    price_tiers: List[Dict[str, Any]] = field(default_factory=list)
    value_proposition_score: float = 0.0
    purchase_triggers: List[Dict[str, Any]] = field(default_factory=list)
    featured_items: List[str] = field(default_factory=list)
    limited_time_offers: List[Dict[str, Any]] = field(default_factory=list)
    starter_pack: Optional[Dict[str, Any]] = None
    total_catalog_value: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "revenue_model_id": self.revenue_model_id,
            "items": [dict(i) for i in self.items],
            "price_tiers": [dict(t) for t in self.price_tiers],
            "value_proposition_score": round(self.value_proposition_score, 2),
            "purchase_triggers": [dict(t) for t in self.purchase_triggers],
            "featured_items": list(self.featured_items),
            "limited_time_offers": [dict(o) for o in self.limited_time_offers],
            "starter_pack": dict(self.starter_pack) if self.starter_pack else None,
            "total_catalog_value": round(self.total_catalog_value, 2),
            "created_at": self.created_at,
        }


@dataclass
class MonetizationAudit:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_id: str = ""
    fairness_score: float = 0.0
    player_sentiment: Dict[str, float] = field(default_factory=dict)
    regulatory_compliance: Dict[str, bool] = field(default_factory=dict)
    revenue_forecast: Dict[str, float] = field(default_factory=dict)
    risk_flags: List[str] = field(default_factory=list)
    improvement_recommendations: List[str] = field(default_factory=list)
    pay_to_win_rating: float = 0.0
    predatory_mechanics_detected: List[str] = field(default_factory=list)
    overall_grade: str = ""
    audited_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "fairness_score": round(self.fairness_score, 2),
            "player_sentiment": {k: round(v, 2) for k, v in self.player_sentiment.items()},
            "regulatory_compliance": dict(self.regulatory_compliance),
            "revenue_forecast": {k: round(v, 2) for k, v in self.revenue_forecast.items()},
            "risk_flags": list(self.risk_flags),
            "improvement_recommendations": list(self.improvement_recommendations),
            "pay_to_win_rating": round(self.pay_to_win_rating, 2),
            "predatory_mechanics_detected": list(self.predatory_mechanics_detected),
            "overall_grade": self.overall_grade,
            "audited_at": self.audited_at,
        }


class AgentMonetizationDesigner:
    """
    Comprehensive game monetization design intelligence system.

    Creates balanced revenue strategies, configures optimal pricing with
    regional sensitivity, maintains healthy virtual economies through
    sink/source analysis, designs in-app purchase catalogs, audits
    monetization fairness, forecasts revenue, and optimizes conversion
    funnels for free-to-paid transitions.

    Usage:
        designer = get_monetization_designer()
        model = designer.design_revenue_model("rpg", "free_game_001")
        pricing = designer.configure_pricing_structure(model)
        economy = designer.balance_virtual_economy("free_game_001")
        catalog = designer.design_iap_catalog("free_game_001", model)
        audit = designer.audit_monetization_fairness("free_game_001")
        forecast = designer.forecast_revenue(model, pricing)
        funnel = designer.optimize_conversion_funnel(model)
    """

    _instance: Optional["AgentMonetizationDesigner"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_PLAYER_BASE = 100000
    _DEFAULT_MONTHS_TO_FORECAST = 12
    _DEFAULT_ECONOMY_SEED = 1000000.0
    _PRICE_PSYCHOLOGY_ENDING = 0.99
    _BUNDLE_DISCOUNT_TIERS = [0.05, 0.10, 0.15, 0.20, 0.25]
    _INFLATION_TARGET_RANGE = (0.01, 0.05)
    _HEALTHY_SINK_SOURCE_RATIO = (0.85, 1.15)

    def __new__(cls) -> "AgentMonetizationDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentMonetizationDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._revenue_models: Dict[str, RevenueModel] = {}
        self._pricing_strategies: Dict[str, PricingStrategy] = {}
        self._economy_snapshots: Dict[str, EconomyBalance] = {}
        self._iap_catalogs: Dict[str, IAPDesign] = {}
        self._audits: Dict[str, MonetizationAudit] = {}
        self._stats: Dict[str, Any] = {
            "models_designed": 0,
            "pricing_configurations": 0,
            "economy_analyses": 0,
            "iap_catalogs_created": 0,
            "audits_performed": 0,
            "revenue_forecasts": 0,
            "funnel_optimizations": 0,
            "models_by_genre": {},
        }

    def design_revenue_model(
        self,
        genre: str,
        game_id: str = "",
        target_arpu: float = 0.0,
        player_base: int = 0,
    ) -> RevenueModel:
        _time_module.sleep(0.001)
        genre_key = genre.lower()
        templates = _GENRE_REVENUE_TEMPLATES.get(
            genre_key, _GENRE_REVENUE_TEMPLATES["casual"]
        )
        baselines = _GENRE_PRICING_BASELINES.get(
            genre_key, _GENRE_PRICING_BASELINES["casual"]
        )

        primary_type = templates[0]
        secondary_types = templates[1:] if len(templates) > 1 else []

        currency_map: Dict[str, List[str]] = {
            RevenueModelType.PREMIUM.value: [CurrencyType.SOFT.value],
            RevenueModelType.FREEMIUM.value: [CurrencyType.SOFT.value, CurrencyType.HARD.value],
            RevenueModelType.SUBSCRIPTION.value: [CurrencyType.PREMIUM.value, CurrencyType.SOFT.value],
            RevenueModelType.BATTLE_PASS.value: [CurrencyType.SEASONAL.value, CurrencyType.SOFT.value],
            RevenueModelType.COSMETIC.value: [CurrencyType.HARD.value, CurrencyType.SOFT.value],
            RevenueModelType.DLC.value: [CurrencyType.PREMIUM.value],
        }

        primary_currency = currency_map.get(primary_type, [CurrencyType.SOFT.value])[0]
        secondary_currencies = currency_map.get(primary_type, [CurrencyType.SOFT.value])[1:]

        pricing_tiers: List[Dict[str, Any]] = []
        if baselines["base_price"] > 0:
            pricing_tiers.append({
                "tier": MonetizationTier.STANDARD.value,
                "price": baselines["base_price"],
                "includes": ["base_game"],
            })
            pricing_tiers.append({
                "tier": MonetizationTier.DELUXE.value,
                "price": round(baselines["base_price"] * 1.40, 2),
                "includes": ["base_game", "season_pass", "exclusive_skin"],
            })
            pricing_tiers.append({
                "tier": MonetizationTier.ULTIMATE.value,
                "price": round(baselines["base_price"] * 1.85, 2),
                "includes": ["base_game", "season_pass", "exclusive_skins", "soundtrack", "art_book"],
            })

        if baselines["battle_pass"] > 0:
            pricing_tiers.append({
                "tier": "battle_pass",
                "price": baselines["battle_pass"],
                "includes": ["seasonal_rewards", "premium_track"],
            })

        if baselines["subscription_monthly"] > 0:
            pricing_tiers.append({
                "tier": "subscription",
                "price": baselines["subscription_monthly"],
                "includes": ["monthly_currency", "exclusive_perks", "ad_free"],
            })

        actual_player_base = player_base if player_base > 0 else self._DEFAULT_PLAYER_BASE
        conversion_base = 0.05
        if primary_type == RevenueModelType.FREEMIUM.value:
            conversion_base = 0.04
        elif primary_type == RevenueModelType.PREMIUM.value:
            conversion_base = 0.95

        arpu = target_arpu if target_arpu > 0 else baselines.get("base_price", 9.99) * conversion_base
        ltv = arpu * 12.0 * (0.6 if primary_type == RevenueModelType.SUBSCRIPTION.value else 1.0)

        if primary_type == RevenueModelType.BATTLE_PASS.value:
            ltv = arpu * 4.0
        elif primary_type == RevenueModelType.COSMETIC.value:
            ltv = arpu * 6.0

        model = RevenueModel(
            model_type=primary_type,
            genre=genre_key,
            pricing_tiers=pricing_tiers,
            primary_currency=primary_currency,
            secondary_currencies=secondary_currencies,
            estimated_arpu=round(arpu, 2),
            conversion_rate_target=round(conversion_base, 4),
            player_lifetime_value=round(ltv, 2),
            market_positioning="premium" if baselines["base_price"] > 49.99 else "standard",
        )

        self._revenue_models[model.id] = model
        self._stats["models_designed"] += 1
        if genre_key not in self._stats["models_by_genre"]:
            self._stats["models_by_genre"][genre_key] = 0
        self._stats["models_by_genre"][genre_key] += 1

        return model

    def configure_pricing_structure(
        self,
        revenue_model: RevenueModel,
        target_regions: Optional[List[str]] = None,
    ) -> PricingStrategy:
        _time_module.sleep(0.001)

        if not revenue_model.pricing_tiers:
            return PricingStrategy(revenue_model_id=revenue_model.id)

        base_tier = revenue_model.pricing_tiers[0]
        base_price = float(base_tier.get("price", 0.0))

        regions = target_regions if target_regions else list(_REGIONAL_MULTIPLIERS.keys())
        regional_prices: Dict[str, float] = {}
        for region in regions:
            multiplier = _REGIONAL_MULTIPLIERS.get(region, 1.0)
            raw_price = base_price * multiplier
            adjusted_price = math.floor(raw_price) + self._PRICE_PSYCHOLOGY_ENDING
            regional_prices[region] = round(max(0.99, adjusted_price), 2)

        discount_schedule: List[Dict[str, Any]] = []
        discount_points = [
            {"days_after_launch": 90, "discount_pct": 0.20},
            {"days_after_launch": 180, "discount_pct": 0.30},
            {"days_after_launch": 270, "discount_pct": 0.40},
            {"days_after_launch": 365, "discount_pct": 0.50},
        ]
        for dp in discount_points:
            discounted = base_price * (1.0 - dp["discount_pct"])
            discount_schedule.append({
                "days_after_launch": dp["days_after_launch"],
                "discount_percentage": dp["discount_pct"],
                "discounted_price": round(math.floor(discounted) + self._PRICE_PSYCHOLOGY_ENDING, 2),
            })

        bundle_configurations: List[Dict[str, Any]] = []
        if len(revenue_model.pricing_tiers) >= 3:
            tiers_for_bundle = revenue_model.pricing_tiers[1:]
            total_unbundled = sum(float(t.get("price", 0)) for t in tiers_for_bundle)
            for i, discount_rate in enumerate(self._BUNDLE_DISCOUNT_TIERS[:3]):
                bundle_price = total_unbundled * (1.0 - discount_rate)
                bundle_configurations.append({
                    "name": f"bundle_tier_{i + 1}",
                    "discount_rate": discount_rate,
                    "bundle_price": round(math.floor(bundle_price) + self._PRICE_PSYCHOLOGY_ENDING, 2),
                    "contents": [t.get("tier", "") for t in tiers_for_bundle],
                    "savings_vs_individual": round(total_unbundled * discount_rate, 2),
                })

        price_anchor = base_price * 1.5 if base_price > 0 else 9.99

        strategy = PricingStrategy(
            revenue_model_id=revenue_model.id,
            base_price_usd=base_price,
            regional_prices=regional_prices,
            discount_schedule=discount_schedule,
            bundle_configurations=bundle_configurations,
            price_anchor=round(price_anchor, 2),
            psychological_pricing_enabled=True,
            dynamic_pricing_enabled=base_price > 19.99,
            min_price=0.99,
            max_price=round(base_price * 2.5, 2),
        )

        self._pricing_strategies[strategy.id] = strategy
        self._stats["pricing_configurations"] += 1

        return strategy

    def balance_virtual_economy(
        self,
        game_id: str,
        player_count: int = 0,
        simulation_days: int = 90,
        initial_currencies: Optional[Dict[str, float]] = None,
    ) -> EconomyBalance:
        _time_module.sleep(0.001)

        actual_players = player_count if player_count > 0 else self._DEFAULT_PLAYER_BASE

        currency_pools: Dict[str, float] = initial_currencies.copy() if initial_currencies else {
            CurrencyType.SOFT.value: self._DEFAULT_ECONOMY_SEED,
            CurrencyType.HARD.value: self._DEFAULT_ECONOMY_SEED * 0.1,
            CurrencyType.PREMIUM.value: 0.0,
            CurrencyType.SEASONAL.value: self._DEFAULT_ECONOMY_SEED * 0.05,
            CurrencyType.GUILD.value: self._DEFAULT_ECONOMY_SEED * 0.02,
        }

        sink_source_ratios: Dict[str, float] = {}
        inflation_trend: List[float] = []
        daily_volume_total = 0.0

        daily_source_rates: Dict[str, float] = {
            CurrencyType.SOFT.value: 500.0,
            CurrencyType.HARD.value: 10.0,
            CurrencyType.SEASONAL.value: 50.0,
            CurrencyType.GUILD.value: 20.0,
        }

        daily_sink_rates: Dict[str, float] = {
            CurrencyType.SOFT.value: 450.0,
            CurrencyType.HARD.value: 9.0,
            CurrencyType.SEASONAL.value: 48.0,
            CurrencyType.GUILD.value: 18.0,
        }

        for day in range(simulation_days):
            day_sources: Dict[str, float] = {}
            day_sinks: Dict[str, float] = {}
            daily_total = 0.0

            for currency, pool in list(currency_pools.items()):
                source_rate = daily_source_rates.get(currency, 100.0)
                sink_rate = daily_sink_rates.get(currency, 90.0)

                source_variation = source_rate * (0.85 + (day % 7) * 0.05)
                sink_variation = sink_rate * (0.90 + (day % 30) * 0.005)

                source_amount = source_variation * actual_players
                sink_amount = sink_variation * actual_players

                day_sources[currency] = source_amount
                day_sinks[currency] = sink_amount

                currency_pools[currency] = max(0.0, pool + source_amount - sink_amount)
                daily_total += source_amount + sink_amount

            daily_volume_total += daily_total

            if day % 7 == 0 and day > 0:
                for currency in list(currency_pools.keys()):
                    if currency_pools[currency] > self._DEFAULT_ECONOMY_SEED * 2:
                        currency_pools[currency] *= 0.97

            if day % 14 == 0 and len(inflation_trend) < 30:
                soft_pool = currency_pools.get(CurrencyType.SOFT.value, self._DEFAULT_ECONOMY_SEED)
                hard_pool = currency_pools.get(CurrencyType.HARD.value, self._DEFAULT_ECONOMY_SEED * 0.1)
                inflation_point = (soft_pool / self._DEFAULT_ECONOMY_SEED + hard_pool / (self._DEFAULT_ECONOMY_SEED * 0.1)) / 2.0
                inflation_trend.append(round(inflation_point - 1.0, 6))

        for currency in currency_pools:
            total_sources = sum(daily_source_rates.get(currency, 0) * actual_players for _ in range(simulation_days))
            total_sinks = sum(daily_sink_rates.get(currency, 0) * actual_players for _ in range(simulation_days))
            if total_sources > 0:
                sink_source_ratios[currency] = round(total_sinks / total_sources, 4)

        inflation_rate = inflation_trend[-1] if inflation_trend else 0.0
        avg_daily_volume = daily_volume_total / max(1, simulation_days)

        wealth_segments = 5
        total_currency_value = sum(currency_pools.values())
        wealth_distribution: Dict[str, float] = {}
        segment_share = total_currency_value / wealth_segments

        distribution_labels = [
            "bottom_20pct", "lower_mid_20pct", "mid_20pct",
            "upper_mid_20pct", "top_20pct",
        ]
        distribution_weights = [0.03, 0.08, 0.15, 0.28, 0.46]
        for i, label in enumerate(distribution_labels):
            wealth_distribution[label] = round(
                segment_share * distribution_weights[i] * wealth_segments, 2
            )

        cum_shares = []
        cum = 0.0
        for weight in distribution_weights:
            cum += weight
            cum_shares.append(cum)
        gini = 0.0
        for i in range(wealth_segments):
            if i == 0:
                ideal = (i + 1) / wealth_segments
            else:
                ideal = (i + 1) / wealth_segments
            actual = cum_shares[i]
            gini += abs(ideal - actual)
        gini_coefficient = round(gini / wealth_segments, 4)

        health_score_base = 0.7
        ratio_health = 0.0
        for ratio in sink_source_ratios.values():
            if self._HEALTHY_SINK_SOURCE_RATIO[0] <= ratio <= self._HEALTHY_SINK_SOURCE_RATIO[1]:
                ratio_health += 1.0
            else:
                deviation = min(abs(ratio - 1.0) / 0.5, 1.0)
                ratio_health += 1.0 - deviation
        if sink_source_ratios:
            ratio_health /= len(sink_source_ratios)

        inflation_health = 0.0
        if self._INFLATION_TARGET_RANGE[0] <= inflation_rate <= self._INFLATION_TARGET_RANGE[1]:
            inflation_health = 1.0
        else:
            inflation_health = max(0.0, 1.0 - abs(inflation_rate - 0.03) / 0.1)

        gini_health = max(0.0, 1.0 - gini_coefficient * 1.5)
        economy_health_score = round(
            health_score_base * 0.3 + ratio_health * 0.3 + inflation_health * 0.25 + gini_health * 0.15, 2
        )

        recommendations: List[str] = []
        for currency, ratio in sink_source_ratios.items():
            if ratio < self._HEALTHY_SINK_SOURCE_RATIO[0]:
                recommendations.append(
                    f"Increase {currency} sinks: ratio {ratio:.3f} below healthy minimum {self._HEALTHY_SINK_SOURCE_RATIO[0]}"
                )
            elif ratio > self._HEALTHY_SINK_SOURCE_RATIO[1]:
                recommendations.append(
                    f"Increase {currency} sources: ratio {ratio:.3f} above healthy maximum {self._HEALTHY_SINK_SOURCE_RATIO[1]}"
                )

        if inflation_rate > self._INFLATION_TARGET_RANGE[1]:
            recommendations.append(
                f"High inflation ({inflation_rate:.4f}): introduce currency sinks and reduce source rates"
            )
        elif inflation_rate < self._INFLATION_TARGET_RANGE[0]:
            recommendations.append(
                f"Low inflation ({inflation_rate:.4f}): increase daily rewards to stimulate economy"
            )

        if gini_coefficient > 0.5:
            recommendations.append(
                f"High wealth inequality (Gini {gini_coefficient:.2f}): add catch-up mechanics for lower segments"
            )

        if not recommendations:
            recommendations.append("Virtual economy appears balanced across all monitored currencies")

        balance = EconomyBalance(
            game_id=game_id,
            currency_pools=currency_pools,
            sink_source_ratios=sink_source_ratios,
            inflation_rate=inflation_rate,
            inflation_trend=inflation_trend,
            wealth_distribution=wealth_distribution,
            gini_coefficient=gini_coefficient,
            daily_active_volume=round(avg_daily_volume, 2),
            economy_health_score=economy_health_score,
            recommendations=recommendations,
        )

        self._economy_snapshots[game_id] = balance
        self._stats["economy_analyses"] += 1

        return balance

    def design_iap_catalog(
        self,
        game_id: str,
        revenue_model: RevenueModel,
        item_count: int = 20,
    ) -> IAPDesign:
        _time_module.sleep(0.001)

        catalog = IAPDesign(
            game_id=game_id,
            revenue_model_id=revenue_model.id,
        )

        consumable_types = [
            {"name": "currency_pack_small", "base_value": 500, "price_mult": 0.99},
            {"name": "currency_pack_medium", "base_value": 1200, "price_mult": 1.99},
            {"name": "currency_pack_large", "base_value": 2800, "price_mult": 4.99},
            {"name": "currency_pack_xl", "base_value": 6500, "price_mult": 9.99},
            {"name": "currency_pack_whale", "base_value": 15000, "price_mult": 19.99},
            {"name": "stamina_refill", "base_value": 100, "price_mult": 0.99},
            {"name": "xp_boost_1h", "base_value": 200, "price_mult": 1.49},
            {"name": "xp_boost_24h", "base_value": 400, "price_mult": 2.99},
            {"name": "loot_box_single", "base_value": 300, "price_mult": 1.99},
            {"name": "loot_box_bundle", "base_value": 1000, "price_mult": 4.99},
            {"name": "retry_token", "base_value": 50, "price_mult": 0.49},
            {"name": "inventory_slot", "base_value": 100, "price_mult": 0.99},
        ]

        cosmetic_types = [
            {"name": "skin_common", "base_value": 500, "price_mult": 2.99},
            {"name": "skin_rare", "base_value": 1200, "price_mult": 5.99},
            {"name": "skin_epic", "base_value": 2500, "price_mult": 9.99},
            {"name": "skin_legendary", "base_value": 5000, "price_mult": 14.99},
            {"name": "emote_pack", "base_value": 300, "price_mult": 1.99},
            {"name": "spray_pack", "base_value": 200, "price_mult": 0.99},
            {"name": "profile_banner", "base_value": 400, "price_mult": 1.99},
            {"name": "loading_screen", "base_value": 350, "price_mult": 1.49},
        ]

        items: List[Dict[str, Any]] = []
        price_tiers: Dict[str, List[Dict[str, Any]]] = {}

        for consumable in consumable_types:
            price = round(math.floor(consumable["price_mult"]) + self._PRICE_PSYCHOLOGY_ENDING, 2)
            value_per_dollar = consumable["base_value"] / max(price, 0.01)

            item = {
                "id": uuid.uuid4().hex,
                "name": consumable["name"],
                "category": "consumable",
                "base_value": consumable["base_value"],
                "price_usd": price,
                "value_per_dollar": round(value_per_dollar, 1),
                "purchase_limit": "unlimited",
            }
            items.append(item)

            tier_key = f"tier_{price:.0f}"
            if tier_key not in price_tiers:
                price_tiers[tier_key] = []
            price_tiers[tier_key].append(item)

        for cosmetic in cosmetic_types:
            price = round(math.floor(cosmetic["price_mult"]) + self._PRICE_PSYCHOLOGY_ENDING, 2)
            value_per_dollar = cosmetic["base_value"] / max(price, 0.01)

            item = {
                "id": uuid.uuid4().hex,
                "name": cosmetic["name"],
                "category": "cosmetic",
                "base_value": cosmetic["base_value"],
                "price_usd": price,
                "value_per_dollar": round(value_per_dollar, 1),
                "purchase_limit": "one_time",
            }
            items.append(item)

            tier_key = f"tier_{price:.0f}"
            if tier_key not in price_tiers:
                price_tiers[tier_key] = []
            price_tiers[tier_key].append(item)

        catalog.items = items
        catalog.price_tiers = [
            {"tier_name": k, "item_count": len(v), "total_value": round(sum(i["price_usd"] for i in v) , 2)}
            for k, v in sorted(price_tiers.items(), key=lambda x: float(x[0].replace("tier_", "")))
        ]

        best_value = max(items, key=lambda x: x["value_per_dollar"])
        worst_value = min(items, key=lambda x: x["value_per_dollar"])
        avg_value_per_dollar = sum(i["value_per_dollar"] for i in items) / max(1, len(items))
        value_spread = (best_value["value_per_dollar"] - worst_value["value_per_dollar"]) / max(avg_value_per_dollar, 0.01)
        catalog.value_proposition_score = round(max(0.0, min(1.0, 1.0 - value_spread * 0.3)), 2)

        catalog.purchase_triggers = [
            {
                "trigger": "starter_pack_offer",
                "timing": "after_tutorial",
                "discount": 0.70,
                "duration_hours": 24,
            },
            {
                "trigger": "first_purchase_bonus",
                "timing": "on_first_purchase",
                "bonus_currency_pct": 100,
            },
            {
                "trigger": "level_up_offer",
                "timing": "every_5_levels",
                "discount": 0.30,
                "duration_hours": 2,
            },
            {
                "trigger": "comeback_offer",
                "timing": "after_7_days_inactive",
                "discount": 0.50,
                "duration_hours": 48,
            },
            {
                "trigger": "season_start_bundle",
                "timing": "season_opening",
                "discount": 0.25,
                "duration_hours": 72,
            },
        ]

        catalog.featured_items = [items[0]["id"], items[5]["id"], items[12]["id"]]

        catalog.limited_time_offers = [
            {
                "name": "weekend_warrior_pack",
                "contents": ["xp_boost_24h", "stamina_refill", "currency_pack_medium"],
                "price": 3.99,
                "regular_price": 7.47,
                "recurrence": "weekly",
            },
            {
                "name": "monthly_mega_bundle",
                "contents": ["currency_pack_large", "skin_rare", "loot_box_bundle"],
                "price": 9.99,
                "regular_price": 17.97,
                "recurrence": "monthly",
            },
        ]

        catalog.starter_pack = {
            "name": "founders_pack",
            "contents": ["currency_pack_medium", "xp_boost_24h", "skin_common"],
            "price": 1.99,
            "regular_price": 7.47,
            "one_time_only": True,
        }

        catalog.total_catalog_value = round(sum(i["price_usd"] for i in items), 2)
        self._iap_catalogs[game_id] = catalog
        self._stats["iap_catalogs_created"] += 1

        return catalog

    def audit_monetization_fairness(
        self,
        game_id: str,
        revenue_model: Optional[RevenueModel] = None,
        iap_catalog: Optional[IAPDesign] = None,
    ) -> MonetizationAudit:
        _time_module.sleep(0.001)

        model = revenue_model
        catalog = iap_catalog if iap_catalog else self._iap_catalogs.get(game_id)

        pay_to_win_score = 0.0
        progression_gating_score = 0.0
        cosmetic_exclusivity_score = 0.0
        price_transparency_score = 0.8
        refund_policy_score = 0.7
        predatory_score = 0.0

        predatory_mechanics: List[str] = []

        if catalog and catalog.items:
            consumable_items = [i for i in catalog.items if i.get("category") == "consumable"]
            cosmetic_items = [i for i in catalog.items if i.get("category") == "cosmetic"]

            if consumable_items:
                max_price = max(i.get("price_usd", 0) for i in consumable_items)
                if max_price > 49.99:
                    predatory_score += 0.30
                    predatory_mechanics.append("ultra_high_price_consumables")

                loot_box_items = [i for i in consumable_items if "loot_box" in i.get("name", "")]
                if loot_box_items:
                    predatory_score += 0.20
                    predatory_mechanics.append("loot_box_randomization")

                currency_efficiency_spread = max(
                    i.get("value_per_dollar", 0) for i in consumable_items
                ) / max(min(i.get("value_per_dollar", 1) for i in consumable_items), 1)
                if currency_efficiency_spread > 3.0:
                    predatory_score += 0.15
                    predatory_mechanics.append("confusing_currency_efficiency")

                has_stamina = any("stamina" in i.get("name", "") for i in consumable_items)
                if has_stamina:
                    progression_gating_score += 0.35
                    if has_stamina and any("xp_boost" in i.get("name", "") for i in consumable_items):
                        pay_to_win_score += 0.40

                boost_items = [i for i in consumable_items if "boost" in i.get("name", "")]
                if boost_items:
                    pay_to_win_score += min(0.5, len(boost_items) * 0.12)

            if cosmetic_items:
                max_cosmetic = max(i.get("price_usd", 0) for i in cosmetic_items)
                if max_cosmetic > 19.99:
                    cosmetic_exclusivity_score += 0.30

                rarity_levels = set()
                for item in cosmetic_items:
                    name = item.get("name", "")
                    if "common" in name:
                        rarity_levels.add("common")
                    elif "rare" in name:
                        rarity_levels.add("rare")
                    elif "epic" in name:
                        rarity_levels.add("epic")
                    elif "legendary" in name:
                        rarity_levels.add("legendary")
                if len(rarity_levels) >= 3:
                    cosmetic_exclusivity_score += 0.20

            if catalog.purchase_triggers:
                trigger_count = len(catalog.purchase_triggers)
                if trigger_count > 4:
                    predatory_score += 0.10
                    predatory_mechanics.append("excessive_purchase_prompts")

                has_fomo = any(
                    t.get("duration_hours", 0) < 4 for t in catalog.purchase_triggers
                )
                if has_fomo:
                    predatory_score += 0.15
                    predatory_mechanics.append("fomo_pressure_tactics")

        if model and model.model_type == RevenueModelType.FREEMIUM.value:
            if model.conversion_rate_target < 0.03:
                progression_gating_score += 0.25

        weighted_scores = {
            "pay_to_win": pay_to_win_score,
            "progression_gating": progression_gating_score,
            "cosmetic_exclusivity": cosmetic_exclusivity_score,
            "price_transparency": 1.0 - price_transparency_score,
            "refund_policy": 1.0 - refund_policy_score,
            "predatory_mechanics": predatory_score,
        }

        fairness_score = 0.0
        for key, weight in _FAIRNESS_WEIGHTS.items():
            fairness_score += weighted_scores.get(key, 0.0) * weight

        fairness_score = round(max(0.0, min(1.0, 1.0 - fairness_score)), 2)

        if fairness_score >= 0.85:
            overall_grade = "A"
        elif fairness_score >= 0.70:
            overall_grade = "B"
        elif fairness_score >= 0.55:
            overall_grade = "C"
        elif fairness_score >= 0.40:
            overall_grade = "D"
        else:
            overall_grade = "F"

        risk_flags: List[str] = []
        if pay_to_win_score > 0.4:
            risk_flags.append("HIGH_P2W: significant competitive advantage purchasable")
        if predatory_score > 0.3:
            risk_flags.append("PREDATORY_PATTERNS: mechanics may exploit vulnerable players")
        if progression_gating_score > 0.4:
            risk_flags.append("PROGRESSION_WALLS: free players face excessive grind")
        if overall_grade in ("D", "F"):
            risk_flags.append("REGULATORY_RISK: model may violate consumer protection guidelines in certain jurisdictions")

        player_sentiment = {
            "perceived_fairness": round(fairness_score + 0.05, 2),
            "value_satisfaction": round(0.5 + (1.0 - cosmetic_exclusivity_score) * 0.3, 2),
            "trust_score": round(0.6 + fairness_score * 0.3, 2),
            "recommendation_likelihood": round(fairness_score * 0.8, 2),
        }

        regulatory_compliance = {
            "loot_box_disclosure": predatory_score < 0.4,
            "price_display_clarity": price_transparency_score > 0.6,
            "refund_mechanism": refund_policy_score > 0.5,
            "dark_pattern_free": predatory_score < 0.3,
            "minor_protections": predatory_score < 0.25,
        }

        monthly_revenue = 0.0
        if model:
            monthly_revenue = model.estimated_arpu * self._DEFAULT_PLAYER_BASE * model.conversion_rate_target

        revenue_forecast = {
            "month_1": round(monthly_revenue, 2),
            "month_3": round(monthly_revenue * 1.15, 2),
            "month_6": round(monthly_revenue * 1.30, 2),
            "month_12": round(monthly_revenue * 1.50, 2),
            "annual_projection": round(monthly_revenue * 13.95, 2),
        }

        improvement_recommendations: List[str] = []
        if pay_to_win_score > 0.3:
            improvement_recommendations.append(
                "Reduce pay-to-win elements: ensure all competitive items are earnable through gameplay"
            )
        if predatory_mechanics:
            improvement_recommendations.append(
                f"Address predatory mechanics: {', '.join(predatory_mechanics)}"
            )
        if progression_gating_score > 0.3:
            improvement_recommendations.append(
                "Reduce free-player progression gating: offer alternative non-monetary paths"
            )
        if cosmetic_exclusivity_score > 0.4:
            improvement_recommendations.append(
                "Lower cosmetic exclusivity pricing to improve accessibility"
            )

        if not improvement_recommendations and overall_grade in ("A", "B"):
            improvement_recommendations.append(
                "Monetization design is well-balanced; monitor player sentiment over time"
            )

        audit = MonetizationAudit(
            game_id=game_id,
            fairness_score=fairness_score,
            player_sentiment=player_sentiment,
            regulatory_compliance=regulatory_compliance,
            revenue_forecast=revenue_forecast,
            risk_flags=risk_flags,
            improvement_recommendations=improvement_recommendations,
            pay_to_win_rating=round(pay_to_win_score, 2),
            predatory_mechanics_detected=predatory_mechanics,
            overall_grade=overall_grade,
        )

        self._audits[game_id] = audit
        self._stats["audits_performed"] += 1

        return audit

    def forecast_revenue(
        self,
        revenue_model: RevenueModel,
        pricing_strategy: Optional[PricingStrategy] = None,
        months: int = 0,
        player_base: int = 0,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        forecast_months = months if months > 0 else self._DEFAULT_MONTHS_TO_FORECAST
        actual_players = player_base if player_base > 0 else self._DEFAULT_PLAYER_BASE

        model_type = revenue_model.model_type
        arpu = revenue_model.estimated_arpu
        conversion = revenue_model.conversion_rate_target

        base_paying_users = actual_players * conversion

        monthly_churn = 0.05
        if model_type == RevenueModelType.SUBSCRIPTION.value:
            monthly_churn = 0.08
        elif model_type == RevenueModelType.BATTLE_PASS.value:
            monthly_churn = 0.15
        elif model_type == RevenueModelType.FREEMIUM.value:
            monthly_churn = 0.12

        monthly_new_players = actual_players * 0.08
        organic_growth_rate = 0.03

        monthly_projections: List[Dict[str, Any]] = []
        cumulative_revenue = 0.0
        current_players = float(actual_players)
        current_paying = base_paying_users

        for month in range(1, forecast_months + 1):
            current_players = current_players * (1.0 - 0.02 + organic_growth_rate) + monthly_new_players
            current_paying = current_paying * (1.0 - monthly_churn) + monthly_new_players * conversion

            month_revenue = current_paying * arpu

            if model_type == RevenueModelType.BATTLE_PASS.value:
                season_multiplier = 2.0 if month % 3 == 1 else 0.6
                month_revenue *= season_multiplier
            elif model_type == RevenueModelType.PREMIUM.value:
                if month > 1:
                    month_revenue *= 0.15

            if pricing_strategy and month > 1:
                for discount in pricing_strategy.discount_schedule:
                    if discount["days_after_launch"] <= month * 30 < discount["days_after_launch"] + 90:
                        month_revenue *= (1.0 + discount["discount_percentage"] * 0.3)

            cumulative_revenue += month_revenue

            monthly_projections.append({
                "month": month,
                "active_players": round(current_players),
                "paying_users": round(current_paying),
                "monthly_revenue": round(month_revenue, 2),
                "cumulative_revenue": round(cumulative_revenue, 2),
                "arpu": round(arpu, 2),
                "conversion_rate": round(
                    current_paying / max(current_players, 1), 4
                ),
            })

        break_even_month = 0
        development_cost = arpu * actual_players * 6.0
        breakeven_target = development_cost * 1.2
        running_total = 0.0
        for proj in monthly_projections:
            running_total = proj["cumulative_revenue"]
            if running_total >= breakeven_target and break_even_month == 0:
                break_even_month = proj["month"]

        final_month = monthly_projections[-1] if monthly_projections else {}
        total_revenue = cumulative_revenue

        result = {
            "revenue_model_id": revenue_model.id,
            "forecast_months": forecast_months,
            "total_projected_revenue": round(total_revenue, 2),
            "average_monthly_revenue": round(total_revenue / max(1, forecast_months), 2),
            "break_even_month": break_even_month,
            "development_cost_estimate": round(development_cost, 2),
            "monthly_projections": monthly_projections,
            "final_month_active_players": final_month.get("active_players", 0) if final_month else 0,
            "final_month_paying_users": final_month.get("paying_users", 0) if final_month else 0,
            "model_type": model_type,
            "generated_at": _time_module.time(),
        }

        self._stats["revenue_forecasts"] += 1

        return result

    def optimize_conversion_funnel(
        self,
        revenue_model: RevenueModel,
        current_funnel: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        funnel = dict(current_funnel) if current_funnel else dict(_DEFAULT_CONVERSION_FUNNEL)

        model_type = revenue_model.model_type
        stage_multipliers: Dict[str, float] = {
            "impression_to_install": 0.02,
            "install_to_tutorial_complete": 0.03,
            "tutorial_to_first_session": 0.02,
            "first_session_to_engaged": 0.04,
            "engaged_to_first_purchase": 0.12,
            "first_purchase_to_repeat": 0.08,
            "repeat_to_subscriber": 0.06,
        }

        if model_type == RevenueModelType.FREEMIUM.value:
            stage_multipliers["impression_to_install"] = 0.04
            stage_multipliers["engaged_to_first_purchase"] = 0.15
        elif model_type == RevenueModelType.SUBSCRIPTION.value:
            stage_multipliers["first_purchase_to_repeat"] = 0.12
            stage_multipliers["repeat_to_subscriber"] = 0.10

        optimized_funnel: Dict[str, float] = {}
        improvement_potentials: Dict[str, Dict[str, Any]] = {}

        for stage, rate in funnel.items():
            multiplier = stage_multipliers.get(stage, 0.05)
            ceiling = min(0.95, rate * 3.0) if rate > 0 else 0.95

            optimization_gain = rate * multiplier
            optimized_rate = min(rate + optimization_gain, ceiling)

            optimized_funnel[stage] = round(optimized_rate, 4)
            improvement_potentials[stage] = {
                "current": round(rate, 4),
                "optimized": round(optimized_rate, 4),
                "improvement_pct": round((optimized_rate - rate) / max(rate, 0.001) * 100, 1),
                "impact_priority": "high" if multiplier > 0.08 else "medium" if multiplier > 0.04 else "low",
            }

        overall_conversion = 1.0
        for rate in funnel.values():
            overall_conversion *= rate

        optimized_overall = 1.0
        for rate in optimized_funnel.values():
            optimized_overall *= rate

        conversion_lift = (
            (optimized_overall - overall_conversion) / max(overall_conversion, 0.0001) * 100
        )

        sorted_improvements = sorted(
            improvement_potentials.items(),
            key=lambda x: x[1]["improvement_pct"],
            reverse=True,
        )

        recommendations: List[str] = []
        for stage, data in sorted_improvements[:5]:
            if data["improvement_pct"] > 1.0:
                stage_display = stage.replace("_", " ").title()
                recommendations.append(
                    f"Focus on '{stage_display}': {data['improvement_pct']:.1f}% potential improvement "
                    f"({data['impact_priority']} priority)"
                )

        if not recommendations:
            recommendations.append("Conversion funnel is well-optimized; maintain current strategies")

        result = {
            "revenue_model_id": revenue_model.id,
            "current_funnel": {k: round(v, 4) for k, v in funnel.items()},
            "optimized_funnel": optimized_funnel,
            "overall_conversion_rate": round(overall_conversion, 6),
            "optimized_overall_conversion": round(optimized_overall, 6),
            "conversion_lift_percentage": round(conversion_lift, 1),
            "stage_improvements": improvement_potentials,
            "top_recommendations": recommendations,
            "generated_at": _time_module.time(),
        }

        self._stats["funnel_optimizations"] += 1

        return result

    def get_revenue_model(self, model_id: str) -> Optional[RevenueModel]:
        _time_module.sleep(0.001)
        return self._revenue_models.get(model_id)

    def get_pricing_strategy(self, strategy_id: str) -> Optional[PricingStrategy]:
        _time_module.sleep(0.001)
        return self._pricing_strategies.get(strategy_id)

    def get_economy_snapshot(self, game_id: str) -> Optional[EconomyBalance]:
        _time_module.sleep(0.001)
        return self._economy_snapshots.get(game_id)

    def get_iap_catalog(self, game_id: str) -> Optional[IAPDesign]:
        _time_module.sleep(0.001)
        return self._iap_catalogs.get(game_id)

    def get_audit(self, game_id: str) -> Optional[MonetizationAudit]:
        _time_module.sleep(0.001)
        return self._audits.get(game_id)

    def list_revenue_models(self) -> List[RevenueModel]:
        _time_module.sleep(0.001)
        return list(self._revenue_models.values())

    def list_iap_catalogs(self) -> List[Dict[str, Any]]:
        """Return all IAP catalogs as dicts."""
        _time_module.sleep(0.001)
        return [c.to_dict() for c in self._iap_catalogs.values()]

    def list_supported_genres(self) -> List[str]:
        _time_module.sleep(0.001)
        return list(_GENRE_REVENUE_TEMPLATES.keys())

    def get_genre_template(self, genre: str) -> Optional[Dict[str, Any]]:
        _time_module.sleep(0.001)
        genre_key = genre.lower()
        templates = _GENRE_REVENUE_TEMPLATES.get(genre_key)
        baselines = _GENRE_PRICING_BASELINES.get(genre_key)
        if templates is None or baselines is None:
            return None
        return {
            "genre": genre_key,
            "recommended_models": list(templates),
            "pricing_baselines": dict(baselines),
        }

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "models_designed": self._stats["models_designed"],
            "models_by_genre": dict(self._stats["models_by_genre"]),
            "pricing_configurations": self._stats["pricing_configurations"],
            "economy_analyses": self._stats["economy_analyses"],
            "iap_catalogs_created": self._stats["iap_catalogs_created"],
            "audits_performed": self._stats["audits_performed"],
            "revenue_forecasts": self._stats["revenue_forecasts"],
            "funnel_optimizations": self._stats["funnel_optimizations"],
            "active_revenue_models": len(self._revenue_models),
            "active_pricing_strategies": len(self._pricing_strategies),
            "economy_snapshots_tracked": len(self._economy_snapshots),
            "iap_catalogs_active": len(self._iap_catalogs),
            "audits_completed": len(self._audits),
            "supported_genres": list(_GENRE_REVENUE_TEMPLATES.keys()),
            "revenue_model_types": [t.value for t in RevenueModelType],
            "currency_types": [c.value for c in CurrencyType],
            "monetization_tiers": [t.value for t in MonetizationTier],
            "supported_regions": len(_REGIONAL_MULTIPLIERS),
        }

    def reset(self) -> None:
        _time_module.sleep(0.001)
        self._revenue_models.clear()
        self._pricing_strategies.clear()
        self._economy_snapshots.clear()
        self._iap_catalogs.clear()
        self._audits.clear()
        self._stats = {
            "models_designed": 0,
            "pricing_configurations": 0,
            "economy_analyses": 0,
            "iap_catalogs_created": 0,
            "audits_performed": 0,
            "revenue_forecasts": 0,
            "funnel_optimizations": 0,
            "models_by_genre": {},
        }


def get_monetization_designer() -> AgentMonetizationDesigner:
    return AgentMonetizationDesigner.get_instance()