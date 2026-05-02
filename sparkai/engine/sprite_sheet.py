"""
Sprite Sheet System - Frame-based sprite animation from sprite sheets and atlases.

Architecture:
    SpriteSheet/
    |-- SheetLayout (grid or irregular frame mapping enumeration)
    |-- FrameDefinition (single frame rect + pivot dataclass)
    |-- AnimationClip (named sequence of frames dataclass)
    |-- SpriteSheetResource (loaded sheet data dataclass)
    |-- SpriteSheetSystem (global sprite sheet orchestration)

Manages sprite sheet resources with frame extraction, animation clip definition,
and runtime playback state. Designed for AI-generated 2D game assets where the
agent can describe frame layouts and the engine handles slicing and rendering.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class SheetLayout(Enum):
    GRID = auto()
    IRREGULAR = auto()
    PACKED = auto()


class LoopMode(Enum):
    ONCE = auto()
    LOOP = auto()
    PING_PONG = auto()
    CLAMP = auto()


@dataclass
class FrameDefinition:
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    rect: Tuple[float, float, float, float] = (0.0, 0.0, 32.0, 32.0)
    pivot: Tuple[float, float] = (0.5, 0.5)
    duration: float = 0.1
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "name": self.name,
            "rect": list(self.rect),
            "pivot": list(self.pivot),
            "duration": self.duration,
        }


@dataclass
class AnimationClip:
    clip_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "idle"
    frames: List[FrameDefinition] = field(default_factory=list)
    loop_mode: LoopMode = LoopMode.LOOP
    speed_multiplier: float = 1.0
    tags: List[str] = field(default_factory=list)

    def get_total_duration(self) -> float:
        return sum(f.duration for f in self.frames) / self.speed_multiplier

    def get_frame_at_time(self, elapsed: float) -> Tuple[FrameDefinition, float]:
        if not self.frames:
            return FrameDefinition(), 0.0

        cycle_duration = self.get_total_duration()

        if self.loop_mode == LoopMode.CLAMP:
            elapsed = min(elapsed, cycle_duration)
        elif self.loop_mode == LoopMode.PING_PONG:
            cycle_count = int(elapsed / cycle_duration)
            elapsed = elapsed % cycle_duration
            if cycle_count % 2 == 1:
                elapsed = cycle_duration - elapsed
        else:
            elapsed = elapsed % cycle_duration

        accumulated = 0.0
        for frame in self.frames:
            frame_dur = frame.duration / self.speed_multiplier
            if accumulated + frame_dur >= elapsed:
                progress = (elapsed - accumulated) / frame_dur if frame_dur > 0 else 1.0
                return frame, progress
            accumulated += frame_dur

        return self.frames[-1], 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "frame_count": len(self.frames),
            "loop_mode": self.loop_mode.name,
            "speed_multiplier": self.speed_multiplier,
            "total_duration": self.get_total_duration(),
            "tags": self.tags,
        }


@dataclass
class SpriteSheetResource:
    sheet_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_path: str = ""
    texture_width: int = 256
    texture_height: int = 256
    layout: SheetLayout = SheetLayout.GRID
    grid_cols: int = 8
    grid_rows: int = 8
    cell_width: int = 32
    cell_height: int = 32
    spacing: int = 0
    margin: int = 0
    frames: List[FrameDefinition] = field(default_factory=list)
    clips: Dict[str, AnimationClip] = field(default_factory=dict)

    def generate_grid_frames(self) -> None:
        self.frames.clear()
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = self.margin + col * (self.cell_width + self.spacing)
                y = self.margin + row * (self.cell_height + self.spacing)
                frame = FrameDefinition(
                    name=f"frame_{row}_{col}",
                    rect=(float(x), float(y), float(self.cell_width), float(self.cell_height)),
                )
                self.frames.append(frame)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_id": self.sheet_id,
            "name": self.name,
            "source_path": self.source_path,
            "texture_size": [self.texture_width, self.texture_height],
            "layout": self.layout.name,
            "grid": [self.grid_cols, self.grid_rows],
            "cell_size": [self.cell_width, self.cell_height],
            "frame_count": len(self.frames),
            "clip_count": len(self.clips),
            "clips": [c.to_dict() for c in self.clips.values()],
        }


class SpriteSheetSystem:
    _instance: Optional["SpriteSheetSystem"] = None

    def __init__(self):
        self._sheets: Dict[str, SpriteSheetResource] = {}
        self._playback_state: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "SpriteSheetSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_sheet(self, name: str, texture_width: int = 256, texture_height: int = 256,
                     grid_cols: int = 8, grid_rows: int = 8, cell_width: int = 32,
                     cell_height: int = 32, layout: SheetLayout = SheetLayout.GRID) -> SpriteSheetResource:
        sheet = SpriteSheetResource(
            name=name,
            texture_width=texture_width,
            texture_height=texture_height,
            layout=layout,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
            cell_width=cell_width,
            cell_height=cell_height,
        )
        if layout == SheetLayout.GRID:
            sheet.generate_grid_frames()
        self._sheets[sheet.sheet_id] = sheet
        return sheet

    def get_sheet(self, sheet_id: str) -> Optional[SpriteSheetResource]:
        return self._sheets.get(sheet_id)

    def remove_sheet(self, sheet_id: str) -> bool:
        if sheet_id in self._sheets:
            del self._sheets[sheet_id]
            return True
        return False

    def list_sheets(self) -> List[SpriteSheetResource]:
        return list(self._sheets.values())

    def create_clip(self, sheet_id: str, name: str, frame_indices: List[int],
                    loop_mode: LoopMode = LoopMode.LOOP,
                    speed_multiplier: float = 1.0,
                    durations: Optional[List[float]] = None) -> Optional[AnimationClip]:
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None

        frames = []
        for i, idx in enumerate(frame_indices):
            if 0 <= idx < len(sheet.frames):
                frame = sheet.frames[idx]
                if durations and i < len(durations):
                    frame = FrameDefinition(
                        name=frame.name,
                        rect=frame.rect,
                        pivot=frame.pivot,
                        duration=durations[i],
                    )
                frames.append(frame)

        if not frames:
            return None

        clip = AnimationClip(
            name=name,
            frames=frames,
            loop_mode=loop_mode,
            speed_multiplier=speed_multiplier,
        )
        sheet.clips[name] = clip
        return clip

    def get_clip(self, sheet_id: str, clip_name: str) -> Optional[AnimationClip]:
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None
        return sheet.clips.get(clip_name)

    def remove_clip(self, sheet_id: str, clip_name: str) -> bool:
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return False
        if clip_name in sheet.clips:
            del sheet.clips[clip_name]
            return True
        return False

    def play(self, entity_id: str, sheet_id: str, clip_name: str,
             speed_multiplier: float = 1.0) -> bool:
        sheet = self._sheets.get(sheet_id)
        if not sheet or clip_name not in sheet.clips:
            return False
        self._playback_state[entity_id] = {
            "sheet_id": sheet_id,
            "clip_name": clip_name,
            "elapsed": 0.0,
            "paused": False,
            "speed_multiplier": speed_multiplier,
        }
        return True

    def update(self, dt: float) -> None:
        for entity_id, state in list(self._playback_state.items()):
            if not state["paused"]:
                state["elapsed"] += dt * state["speed_multiplier"]

    def get_current_frame(self, entity_id: str) -> Optional[Tuple[FrameDefinition, float]]:
        state = self._playback_state.get(entity_id)
        if not state:
            return None
        sheet = self._sheets.get(state["sheet_id"])
        if not sheet:
            return None
        clip = sheet.clips.get(state["clip_name"])
        if not clip:
            return None
        return clip.get_frame_at_time(state["elapsed"])

    def pause(self, entity_id: str) -> bool:
        if entity_id in self._playback_state:
            self._playback_state[entity_id]["paused"] = True
            return True
        return False

    def resume(self, entity_id: str) -> bool:
        if entity_id in self._playback_state:
            self._playback_state[entity_id]["paused"] = False
            return True
        return False

    def stop(self, entity_id: str) -> bool:
        if entity_id in self._playback_state:
            del self._playback_state[entity_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total_frames = sum(len(s.frames) for s in self._sheets.values())
        total_clips = sum(len(s.clips) for s in self._sheets.values())
        return {
            "sheet_count": len(self._sheets),
            "total_frames": total_frames,
            "total_clips": total_clips,
            "playback_count": len(self._playback_state),
            "playing": sum(1 for s in self._playback_state.values() if not s["paused"]),
        }


def get_sprite_sheet_system() -> SpriteSheetSystem:
    return SpriteSheetSystem.get_instance()
