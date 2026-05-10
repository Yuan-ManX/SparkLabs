"""
SparkLabs Engine - Combat System

Turn-based and real-time combat resolution engine for
AI-native games. Manages combat units, status effects,
action resolution with damage calculations, and victory
condition evaluation. Supports configurable turn order,
element-based modifiers, and status effect stacking.

Architecture:
  CombatSystem
    |-- CombatUnit (stats, status effects, action pool)
    |-- CombatAction (action type, target, base power)
    |-- DamageCalculator (stat-driven with element modifiers)
    |-- StatusEffectManager (duration, stacking, cleanup)
    |-- TurnOrderEngine (speed-based initiative sorting)

Action Types:
  - ATTACK: basic damage based on attack stat
  - DEFEND: reduce incoming damage for one round
  - SKILL: special ability with custom effects and cooldown
  - ITEM: consume inventory item for healing/buffing
  - FLEE: attempt to escape combat
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CombatActionType(Enum):
    ATTACK = "attack"
    DEFEND = "defend"
    SKILL = "skill"
    ITEM = "item"
    FLEE = "flee"
    WAIT = "wait"


class CombatMode(Enum):
    TURN_BASED = "turn_based"
    REAL_TIME = "real_time"


class Element(Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    AIR = "air"
    LIGHT = "light"
    DARK = "dark"
    NONE = "none"


@dataclass
class StatusEffect:
    effect_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    duration: int = 1
    remaining_duration: int = 1
    stat_modifiers: Dict[str, float] = field(default_factory=dict)
    damage_per_turn: int = 0
    healing_per_turn: int = 0
    is_stun: bool = False
    is_beneficial: bool = False
    element: Element = Element.NONE


@dataclass
class CombatUnit:
    unit_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    team_id: int = 0
    max_hp: int = 100
    current_hp: int = 100
    attack: int = 10
    defense: int = 5
    speed: int = 10
    level: int = 1
    element: Element = Element.PHYSICAL
    status_effects: List[StatusEffect] = field(default_factory=list)
    is_defending: bool = False
    is_alive: bool = True
    skills: List[str] = field(default_factory=list)

    def take_damage(self, amount: int) -> int:
        damage = amount
        if self.is_defending:
            damage = max(1, damage // 2)
            self.is_defending = False
        damage = max(1, damage - self.defense // 2)
        self.current_hp = max(0, self.current_hp - damage)
        if self.current_hp <= 0:
            self.is_alive = False
        return damage

    def heal(self, amount: int) -> int:
        healing = min(amount, self.max_hp - self.current_hp)
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return healing

    def apply_status(self, effect: StatusEffect) -> None:
        existing = next(
            (e for e in self.status_effects if e.name == effect.name), None
        )
        if existing:
            existing.remaining_duration = effect.duration
        else:
            self.status_effects.append(effect)

    def tick_statuses(self) -> List[str]:
        expired: List[str] = []
        for effect in self.status_effects[:]:
            if effect.damage_per_turn > 0:
                self.take_damage(effect.damage_per_turn)
            if effect.healing_per_turn > 0:
                self.heal(effect.healing_per_turn)
            effect.remaining_duration -= 1
            if effect.remaining_duration <= 0:
                self.status_effects.remove(effect)
                expired.append(effect.name)
        return expired

    def is_stunned(self) -> bool:
        return any(e.is_stun for e in self.status_effects)


@dataclass
class CombatAction:
    action_type: CombatActionType
    actor: str
    target: str = ""
    skill_name: str = ""
    item_name: str = ""


@dataclass
class CombatState:
    battle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    units: Dict[str, CombatUnit] = field(default_factory=dict)
    turn_order: List[str] = field(default_factory=list)
    current_turn: int = 0
    current_unit_index: int = 0
    round_number: int = 1
    mode: CombatMode = CombatMode.TURN_BASED
    is_active: bool = False
    started_at: float = 0.0
    action_log: List[Dict[str, Any]] = field(default_factory=list)
    victory_team: int = -1


class CombatSystem:
    """
    Combat resolution engine supporting turn-based and
    real-time modes with status effects and element modifiers.
    """

    _instance: Optional[CombatSystem] = None
    ELEMENT_EFFECTIVENESS: Dict[str, Dict[str, float]] = {
        "fire": {"earth": 1.5, "water": 0.75, "air": 1.25},
        "water": {"fire": 1.5, "earth": 0.75, "water": 0.75},
        "earth": {"air": 1.5, "water": 1.25, "fire": 0.75},
        "air": {"earth": 1.5, "fire": 0.75, "air": 0.75},
        "light": {"dark": 2.0, "light": 0.5},
        "dark": {"light": 2.0, "dark": 0.5},
    }

    @classmethod
    def get_instance(cls) -> CombatSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._battles: Dict[str, CombatState] = {}
        self._battle_count: int = 0
        self._total_actions: int = 0

    def create_unit(
        self,
        name: str,
        team_id: int = 0,
        max_hp: int = 100,
        attack: int = 10,
        defense: int = 5,
        speed: int = 10,
        element: str = "physical",
    ) -> CombatUnit:
        elem = Element(element) if element in Element._value2member_map_ else Element.PHYSICAL
        return CombatUnit(
            name=name,
            team_id=team_id,
            max_hp=max_hp,
            current_hp=max_hp,
            attack=attack,
            defense=defense,
            speed=speed,
            element=elem,
        )

    def initiate_combat(
        self,
        units: List[CombatUnit],
        mode: CombatMode = CombatMode.TURN_BASED,
    ) -> str:
        state = CombatState(mode=mode, is_active=True, started_at=time.time())
        for unit in units:
            state.units[unit.unit_id] = unit
        state.turn_order = sorted(
            state.units.keys(),
            key=lambda uid: state.units[uid].speed,
            reverse=True,
        )
        self._battles[state.battle_id] = state
        self._battle_count += 1
        return state.battle_id

    def execute_action(self, battle_id: str, action: CombatAction) -> Dict[str, Any]:
        state = self._battles.get(battle_id)
        if state is None or not state.is_active:
            return {"success": False, "reason": "battle not active"}

        actor = state.units.get(action.actor)
        if actor is None or not actor.is_alive:
            return {"success": False, "reason": "invalid actor"}

        if actor.is_stunned():
            result = {
                "success": True,
                "action": "stunned",
                "actor": actor.name,
                "message": f"{actor.name} is stunned and cannot act!",
            }
            state.action_log.append(result)
            return result

        result: Dict[str, Any] = {}

        if action.action_type == CombatActionType.ATTACK:
            result = self._resolve_attack(state, actor, action.target)
        elif action.action_type == CombatActionType.DEFEND:
            actor.is_defending = True
            result = {
                "success": True,
                "action": "defend",
                "actor": actor.name,
                "message": f"{actor.name} takes a defensive stance!",
            }
        elif action.action_type == CombatActionType.FLEE:
            result = self._resolve_flee(state, actor)
        elif action.action_type == CombatActionType.WAIT:
            result = {
                "success": True,
                "action": "wait",
                "actor": actor.name,
                "message": f"{actor.name} waits.",
            }
        else:
            result = {"success": False, "reason": f"unsupported action: {action.action_type}"}

        self._total_actions += 1
        state.action_log.append(result)
        self._check_victory(state)
        return result

    def _resolve_attack(
        self,
        state: CombatState,
        actor: CombatUnit,
        target_id: str,
    ) -> Dict[str, Any]:
        target = state.units.get(target_id)
        if target is None or not target.is_alive:
            return {"success": False, "reason": "invalid target"}

        variation = random.uniform(0.85, 1.15)
        base_damage = int(actor.attack * variation)

        element_mult = 1.0
        element_map = self.ELEMENT_EFFECTIVENESS.get(actor.element.value, {})
        element_mult = element_map.get(target.element.value, 1.0)

        if element_mult > 1.0:
            effectiveness = "super effective"
        elif element_mult < 1.0:
            effectiveness = "not very effective"
        else:
            effectiveness = "normal"

        base_damage = int(base_damage * element_mult)

        is_critical = random.random() < 0.1
        if is_critical:
            base_damage = int(base_damage * 2.0)

        actual_damage = target.take_damage(base_damage)

        return {
            "success": True,
            "action": "attack",
            "actor": actor.name,
            "target": target.name,
            "damage": actual_damage,
            "critical": is_critical,
            "effectiveness": effectiveness,
            "target_hp": target.current_hp,
            "target_defeated": not target.is_alive,
        }

    def _resolve_flee(
        self,
        state: CombatState,
        actor: CombatUnit,
    ) -> Dict[str, Any]:
        actor.is_alive = False
        return {
            "success": True,
            "action": "flee",
            "actor": actor.name,
            "message": f"{actor.name} fled from battle!",
        }

    def apply_status(
        self,
        battle_id: str,
        target_id: str,
        effect: StatusEffect,
    ) -> bool:
        state = self._battles.get(battle_id)
        if state is None:
            return False
        target = state.units.get(target_id)
        if target is None:
            return False
        target.apply_status(effect)
        return True

    def advance_turn(self, battle_id: str) -> Dict[str, Any]:
        state = self._battles.get(battle_id)
        if state is None or not state.is_active:
            return {"success": False}

        live_units = [
            uid
            for uid in state.turn_order
            if state.units.get(uid) and state.units[uid].is_alive
        ]

        if not live_units:
            state.is_active = False
            return {"success": True, "battle_over": True}

        state.current_unit_index = (state.current_unit_index + 1) % len(state.units)
        if state.current_unit_index == 0:
            state.round_number += 1
            for unit in state.units.values():
                if unit.is_alive:
                    unit.tick_statuses()

        current_id = list(state.units.keys())[state.current_unit_index]
        current_unit = state.units.get(current_id)
        while current_unit is None or not current_unit.is_alive:
            state.current_unit_index = (state.current_unit_index + 1) % len(state.units)
            if state.current_unit_index == 0:
                state.round_number += 1
                for unit in state.units.values():
                    if unit.is_alive:
                        unit.tick_statuses()
                    break
            current_id = list(state.units.keys())[state.current_unit_index]
            current_unit = state.units.get(current_id)

        return {
            "success": True,
            "current_unit": current_unit.name if current_unit else "",
            "round": state.round_number,
        }

    def _check_victory(self, state: CombatState) -> None:
        teams_alive: Dict[int, bool] = {}
        for unit in state.units.values():
            if unit.is_alive:
                teams_alive[unit.team_id] = True
        surviving_teams = list(teams_alive.keys())
        if len(surviving_teams) <= 1:
            state.is_active = False
            state.victory_team = surviving_teams[0] if surviving_teams else -1

    def check_victory(self, battle_id: str) -> Dict[str, Any]:
        state = self._battles.get(battle_id)
        if state is None:
            return {"is_over": False}
        return {
            "is_over": not state.is_active,
            "victory_team": state.victory_team if state.victory_team >= 0 else None,
            "round_number": state.round_number,
            "action_count": len(state.action_log),
        }

    def get_battle_state(self, battle_id: str) -> Optional[Dict[str, Any]]:
        state = self._battles.get(battle_id)
        if state is None:
            return None
        return {
            "battle_id": state.battle_id,
            "is_active": state.is_active,
            "round": state.round_number,
            "mode": state.mode.value,
            "units": [
                {
                    "unit_id": u.unit_id,
                    "name": u.name,
                    "team": u.team_id,
                    "hp": u.current_hp,
                    "max_hp": u.max_hp,
                    "alive": u.is_alive,
                    "statuses": [s.name for s in u.status_effects],
                }
                for u in state.units.values()
            ],
            "action_count": len(state.action_log),
        }

    def get_stats(self) -> Dict[str, Any]:
        active_battles = sum(1 for b in self._battles.values() if b.is_active)
        total_units = sum(len(b.units) for b in self._battles.values())
        total_rounds = sum(b.round_number for b in self._battles.values())
        return {
            "total_battles": self._battle_count,
            "active_battles": active_battles,
            "total_units": total_units,
            "total_actions": self._total_actions,
            "total_rounds": total_rounds,
            "elements": [e.value for e in Element],
        }

    def reset(self) -> None:
        self._battles.clear()


_combat_system = CombatSystem.get_instance()


def get_combat_system() -> CombatSystem:
    return _combat_system