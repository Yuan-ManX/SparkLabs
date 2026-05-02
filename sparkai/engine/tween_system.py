"""
Tween System - Interpolation animation for smooth property transitions.

Architecture:
    TweenSystem/
    |-- EasingType (interpolation curve enumeration)
    |-- TweenTarget (animated property descriptor dataclass)
    |-- TweenInstance (active tween with runtime state dataclass)
    |-- TweenGroup (parallel/sequenced tween collection dataclass)
    |-- TweenSystem (global tween orchestration)

Provides smooth, frame-rate-independent property animations for AI-generated
games. Supports position, scale, rotation, color, and custom numeric properties
with configurable easing curves, looping, and parallel/sequential composition.
"""

from __future__ import annotations

import uuid
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class EasingType(Enum):
    LINEAR = auto()
    EASE_IN_QUAD = auto()
    EASE_OUT_QUAD = auto()
    EASE_IN_OUT_QUAD = auto()
    EASE_IN_CUBIC = auto()
    EASE_OUT_CUBIC = auto()
    EASE_IN_OUT_CUBIC = auto()
    EASE_IN_ELASTIC = auto()
    EASE_OUT_ELASTIC = auto()
    EASE_IN_OUT_ELASTIC = auto()
    EASE_IN_BOUNCE = auto()
    EASE_OUT_BOUNCE = auto()
    EASE_IN_OUT_BOUNCE = auto()
    EASE_IN_BACK = auto()
    EASE_OUT_BACK = auto()
    EASE_IN_OUT_BACK = auto()
    SINE_IN = auto()
    SINE_OUT = auto()
    SINE_IN_OUT = auto()


class TweenLoopMode(Enum):
    ONCE = auto()
    REPEAT = auto()
    PING_PONG = auto()
    REPEAT_FOREVER = auto()


@dataclass
class TweenTarget:
    target_id: str = ""
    property_name: str = ""
    start_value: float = 0.0
    end_value: float = 1.0
    getter: Optional[Callable[[], float]] = None
    setter: Optional[Callable[[float], None]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "property": self.property_name,
            "start": self.start_value,
            "end": self.end_value,
        }


@dataclass
class TweenInstance:
    tween_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: TweenTarget = field(default_factory=TweenTarget)
    duration: float = 0.5
    delay: float = 0.0
    easing: EasingType = EasingType.EASE_IN_OUT_QUAD
    loop_mode: TweenLoopMode = TweenLoopMode.ONCE
    elapsed: float = 0.0
    elapsed_delay: float = 0.0
    current_value: float = 0.0
    progress: float = 0.0
    active: bool = True
    reversed: bool = False
    on_complete: Optional[Callable[[], None]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tween_id": self.tween_id,
            "target": self.target.to_dict(),
            "duration": self.duration,
            "easing": self.easing.name,
            "progress": round(self.progress, 3),
            "current_value": round(self.current_value, 3),
            "active": self.active,
        }


@dataclass
class TweenGroup:
    group_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Group"
    tweens: List[TweenInstance] = field(default_factory=list)
    parallel: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "tween_count": len(self.tweens),
            "parallel": self.parallel,
            "active": any(t.active for t in self.tweens),
        }


class TweenSystem:
    _instance: Optional["TweenSystem"] = None

    def __init__(self):
        self._tweens: Dict[str, TweenInstance] = {}
        self._groups: Dict[str, TweenGroup] = {}
        self._total_created: int = 0
        self._total_completed: int = 0

    @classmethod
    def get_instance(cls) -> "TweenSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create(self, target_id: str, property_name: str, start_value: float, end_value: float,
               duration: float = 0.5,
               easing: Any = None,
               delay: float = 0.0,
               loop_mode: Any = None,
               on_complete: Optional[Callable[[], None]] = None) -> TweenInstance:
        if easing is None:
            easing = EasingType.EASE_IN_OUT_QUAD
        elif isinstance(easing, str):
            try:
                easing = EasingType[easing.upper()]
            except KeyError:
                easing = EasingType.LINEAR
        if loop_mode is None:
            loop_mode = TweenLoopMode.ONCE
        elif isinstance(loop_mode, str):
            try:
                loop_mode = TweenLoopMode[loop_mode.upper()]
            except KeyError:
                loop_mode = TweenLoopMode.ONCE
        delay = float(delay)
        actual_start = float(start_value)
        target = TweenTarget(
            target_id=target_id,
            property_name=property_name,
            start_value=actual_start,
            end_value=end_value,
        )
        tween = TweenInstance(
            target=target,
            duration=max(0.001, duration),
            delay=delay,
            easing=easing,
            loop_mode=loop_mode,
            current_value=actual_start,
            on_complete=on_complete,
        )
        self._tweens[tween.tween_id] = tween
        self._total_created += 1
        return tween

    def create_group(self, name: str = "Group", tweens: Optional[List[TweenInstance]] = None,
                     parallel: bool = True) -> TweenGroup:
        group = TweenGroup(name=name, tweens=tweens or [], parallel=parallel)
        self._groups[group.group_id] = group
        return group

    def apply_easing(self, t: float, easing: EasingType) -> float:
        t = max(0.0, min(1.0, t))

        if easing == EasingType.LINEAR:
            return t

        elif easing == EasingType.EASE_IN_QUAD:
            return t * t
        elif easing == EasingType.EASE_OUT_QUAD:
            return t * (2 - t)
        elif easing == EasingType.EASE_IN_OUT_QUAD:
            return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

        elif easing == EasingType.EASE_IN_CUBIC:
            return t * t * t
        elif easing == EasingType.EASE_OUT_CUBIC:
            t -= 1
            return t * t * t + 1
        elif easing == EasingType.EASE_IN_OUT_CUBIC:
            return 4 * t * t * t if t < 0.5 else (t - 1) * (2 * t - 2) * (2 * t - 2) + 1

        elif easing == EasingType.EASE_IN_ELASTIC:
            if t == 0 or t == 1:
                return t
            return -math.pow(2, 10 * (t - 1)) * math.sin((t - 1.075) * (2 * math.pi) / 0.3)
        elif easing == EasingType.EASE_OUT_ELASTIC:
            if t == 0 or t == 1:
                return t
            return math.pow(2, -10 * t) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1
        elif easing == EasingType.EASE_IN_OUT_ELASTIC:
            if t == 0 or t == 1:
                return t
            t *= 2
            if t < 1:
                return -0.5 * math.pow(2, 10 * (t - 1)) * math.sin((t - 1.075) * (2 * math.pi) / 0.3)
            return 0.5 * math.pow(2, -10 * (t - 1)) * math.sin((t - 1.075) * (2 * math.pi) / 0.3) + 1

        elif easing == EasingType.EASE_IN_BOUNCE:
            return 1 - self.apply_easing(1 - t, EasingType.EASE_OUT_BOUNCE)
        elif easing == EasingType.EASE_OUT_BOUNCE:
            if t < 1 / 2.75:
                return 7.5625 * t * t
            elif t < 2 / 2.75:
                t -= 1.5 / 2.75
                return 7.5625 * t * t + 0.75
            elif t < 2.5 / 2.75:
                t -= 2.25 / 2.75
                return 7.5625 * t * t + 0.9375
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
        elif easing == EasingType.EASE_IN_OUT_BOUNCE:
            if t < 0.5:
                return (1 - self.apply_easing(1 - 2 * t, EasingType.EASE_OUT_BOUNCE)) / 2
            return (1 + self.apply_easing(2 * t - 1, EasingType.EASE_OUT_BOUNCE)) / 2

        elif easing == EasingType.EASE_IN_BACK:
            s = 1.70158
            return t * t * ((s + 1) * t - s)
        elif easing == EasingType.EASE_OUT_BACK:
            s = 1.70158
            t -= 1
            return t * t * ((s + 1) * t + s) + 1
        elif easing == EasingType.EASE_IN_OUT_BACK:
            s = 1.70158 * 1.525
            t *= 2
            if t < 1:
                return 0.5 * (t * t * ((s + 1) * t - s))
            t -= 2
            return 0.5 * (t * t * ((s + 1) * t + s) + 2)

        elif easing == EasingType.SINE_IN:
            return 1 - math.cos(t * math.pi / 2)
        elif easing == EasingType.SINE_OUT:
            return math.sin(t * math.pi / 2)
        elif easing == EasingType.SINE_IN_OUT:
            return -(math.cos(math.pi * t) - 1) / 2

        return t

    def update(self, dt: float) -> None:
        completed_ids = []

        for tween_id, tween in self._tweens.items():
            if not tween.active:
                continue

            if tween.elapsed_delay < tween.delay:
                tween.elapsed_delay += dt
                continue

            tween.elapsed += dt
            raw_progress = min(1.0, tween.elapsed / tween.duration)
            eased = self.apply_easing(raw_progress, tween.easing)
            tween.progress = eased
            tween.current_value = (
                tween.target.start_value +
                (tween.target.end_value - tween.target.start_value) * eased
            )

            if tween.target.setter:
                tween.target.setter(tween.current_value)

            if raw_progress >= 1.0:
                if tween.loop_mode == TweenLoopMode.REPEAT:
                    tween.elapsed = 0.0
                elif tween.loop_mode == TweenLoopMode.REPEAT_FOREVER:
                    tween.elapsed = 0.0
                elif tween.loop_mode == TweenLoopMode.PING_PONG:
                    tween.target.start_value, tween.target.end_value = (
                        tween.target.end_value, tween.target.start_value
                    )
                    tween.elapsed = 0.0
                else:
                    tween.active = False
                    completed_ids.append(tween_id)
                    self._total_completed += 1
                    if tween.on_complete:
                        try:
                            tween.on_complete()
                        except Exception:
                            pass

        for tween_id in completed_ids:
            self._tweens.pop(tween_id, None)

    def pause(self, tween_id: str) -> bool:
        tween = self._tweens.get(tween_id)
        if tween:
            tween.active = False
            return True
        return False

    def resume(self, tween_id: str) -> bool:
        tween = self._tweens.get(tween_id)
        if tween:
            tween.active = True
            return True
        return False

    def cancel(self, tween_id: str) -> bool:
        if tween_id in self._tweens:
            self._tweens[tween_id].active = False
            del self._tweens[tween_id]
            return True
        return False

    def list_tweens(self) -> List[TweenInstance]:
        return list(self._tweens.values())

    def list_groups(self) -> List[TweenGroup]:
        return list(self._groups.values())

    def get_stats(self) -> Dict[str, Any]:
        active_tweens = sum(1 for t in self._tweens.values() if t.active)
        paused_tweens = len(self._tweens) - active_tweens
        return {
            "total_created": self._total_created,
            "total_completed": self._total_completed,
            "active_tweens": active_tweens,
            "paused_tweens": paused_tweens,
            "group_count": len(self._groups),
        }


def get_tween_system() -> TweenSystem:
    return TweenSystem.get_instance()
