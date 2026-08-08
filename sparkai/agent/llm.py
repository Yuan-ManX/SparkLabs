"""
SparkAI Agent - LLM Provider Integration

Supports multiple LLM backends plus a simulation mode that generates
contextually relevant responses without requiring API keys.
"""

from __future__ import annotations

import json
import re
import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    provider: str = "simulation"
    model: str = "spark-sim-v1"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    timeout: float = 60.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


class SimulationEngine:
    """
    Rule-based response generator that produces contextually relevant
    outputs without requiring an actual LLM backend. Supports game
    design, code generation, narrative, and verification scenarios.
    """

    _game_keywords = {
        "rpg": {"genre": "rpg", "mechanics": ["turn-based-combat", "skill-tree", "quest-system", "inventory-system"], "style": "pixel-art"},
        "platformer": {"genre": "platformer", "mechanics": ["physics-puzzle", "exploration"], "style": "side-scrolling"},
        "puzzle": {"genre": "puzzle", "mechanics": ["physics-puzzle", "resource-management"], "style": "stylized"},
        "strategy": {"genre": "strategy", "mechanics": ["resource-management", "skill-tree"], "style": "low-poly"},
        "adventure": {"genre": "adventure", "mechanics": ["exploration", "dialogue-tree", "quest-system"], "style": "hand-drawn"},
        "shooter": {"genre": "shooter", "mechanics": ["real-time-combat"], "style": "realistic"},
        "sandbox": {"genre": "sandbox", "mechanics": ["procedural-generation", "crafting", "exploration"], "style": "voxel"},
    }

    _action_templates = [
        "Create a new {entity_type} named '{name}' with {count} components",
        "Modify {entity_type} '{name}' by adding {component}",
        "Generate {count} {entity_type}s with {style} aesthetic",
        "Set {entity_type} '{name}' property {prop} to {value}",
        "Spawn {count} {entity_type}s around {location}",
    ]

    _verification_responses = {
        "default": '{"verified": true, "confidence": 0.85, "notes": "All checks passed successfully"}',
        "fail": '{"verified": false, "confidence": 0.2, "notes": "Verification criteria not met"}',
        "low": '{"verified": true, "confidence": 0.4, "notes": "Partially verified, needs review"}',
    }

    @classmethod
    def generate(cls, prompt: str, temperature: float = 0.7) -> str:
        prompt_lower = prompt.lower()

        if "verify" in prompt_lower or "verification" in prompt_lower:
            return cls._verify_response(prompt)

        if "plan" in prompt_lower and ("game" in prompt_lower or "create" in prompt_lower or "build" in prompt_lower):
            return cls._game_plan_response(prompt)

        if "game" in prompt_lower and ("create" in prompt_lower or "design" in prompt_lower or "build" in prompt_lower or "description" in prompt_lower):
            return cls._game_creation_response(prompt)

        if "code" in prompt_lower or "generate" in prompt_lower or "script" in prompt_lower:
            return cls._code_response(prompt)

        if "narrative" in prompt_lower or "story" in prompt_lower or "dialogue" in prompt_lower:
            return cls._narrative_response(prompt)

        if "entity" in prompt_lower or "spawn" in prompt_lower or "create" in prompt_lower:
            return cls._entity_response(prompt)

        if "scene" in prompt_lower or "world" in prompt_lower:
            return cls._scene_response(prompt)

        if "quest" in prompt_lower or "mission" in prompt_lower:
            return cls._quest_response(prompt)

        if "npc" in prompt_lower or "character" in prompt_lower:
            return cls._npc_response(prompt)

        if "physics" in prompt_lower or "collision" in prompt_lower:
            return cls._physics_response(prompt)

        if "analyze" in prompt_lower or "evaluate" in prompt_lower or "review" in prompt_lower:
            return cls._analysis_response(prompt)

        if "error" in prompt_lower or "fix" in prompt_lower or "debug" in prompt_lower:
            return cls._fix_response(prompt)

        return cls._generic_response(prompt, temperature)

    @classmethod
    def _verify_response(cls, prompt: str) -> str:
        if "fail" in prompt.lower() or "error" in prompt.lower():
            return cls._verification_responses["fail"]
        if "partially" in prompt.lower() or "low" in prompt.lower():
            return cls._verification_responses["low"]
        return cls._verification_responses["default"]

    @classmethod
    def _game_plan_response(cls, prompt: str) -> str:
        return json.dumps({
            "status_quo": "Empty project with no game content",
            "target_end_state": "A playable game with core mechanics, a scene, entities, and UI",
            "checklist": [
                "Define game genre and core mechanics",
                "Create main scene with lighting and camera",
                "Spawn player entity with movement controls",
                "Add NPC entities with basic AI behaviors",
                "Set up physics and collision detection",
                "Implement UI overlay with health and score",
                "Playtest and iterate on difficulty",
            ],
            "work_plan": [
                {"description": "Parse game description and detect genre", "action": "parse_description", "params": {}},
                {"description": "Create project with detected settings", "action": "create_project", "params": {}},
                {"description": "Set up main scene with entities", "action": "setup_scene", "params": {}},
                {"description": "Configure physics and input", "action": "configure_physics", "params": {}},
                {"description": "Generate narrative content", "action": "generate_narrative", "params": {}},
                {"description": "Create UI overlays", "action": "create_ui", "params": {}},
                {"description": "Run playtest simulation", "action": "run_playtest", "params": {}},
            ],
            "verification_gates": [
                "Game loads without errors",
                "Player can move and interact",
                "NPCs exhibit basic behaviors",
                "UI displays correct information",
            ],
        }, indent=2)

    @classmethod
    def _game_creation_response(cls, prompt: str) -> str:
        prompt_lower = prompt.lower()
        detected_genre = "adventure"
        for genre in cls._game_keywords:
            if genre in prompt_lower:
                detected_genre = genre
                break

        genre_data = cls._game_keywords.get(detected_genre, cls._game_keywords["adventure"])
        return json.dumps({
            "project": {
                "name": f"SparkLabs_{detected_genre.capitalize()}_Game",
                "genre": detected_genre,
                "description": prompt[:200],
                "mechanics": genre_data["mechanics"],
                "visual_style": genre_data["style"],
            },
            "entities": [
                {"type": "player", "name": "Hero", "components": ["transform", "physics", "input", "health"]},
                {"type": "npc", "name": "Villager", "components": ["transform", "ai", "dialogue"]},
                {"type": "enemy", "name": "Guardian", "components": ["transform", "physics", "combat", "ai"]},
                {"type": "item", "name": "Treasure", "components": ["transform", "inventory"]},
            ],
            "scenes": [
                {"name": "Main Menu", "type": "ui"},
                {"name": "Town", "type": "exploration"},
                {"name": "Dungeon", "type": "combat"},
                {"name": "Victory", "type": "ending"},
            ],
            "systems": {
                "physics": "enabled",
                "collision": "enabled",
                "ai": "enabled",
                "dialogue": "enabled",
                "inventory": "enabled",
                "save": "enabled",
            },
        }, indent=2)

    @classmethod
    def _code_response(cls, prompt: str) -> str:
        if "entity" in prompt.lower() or "class" in prompt.lower():
            return '''Here is the generated code:

```python
class GameEntity:
    def __init__(self, name, entity_type="generic"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.entity_type = entity_type
        self.components = {}
        self.position = [0, 0, 0]
        self.rotation = [0, 0, 0]
        self.scale = [1, 1, 1]
        self.active = True

    def add_component(self, comp_type, data=None):
        self.components[comp_type] = data or {}

    def update(self, dt):
        for comp in self.components.values():
            if hasattr(comp, 'update'):
                comp.update(dt)
```'''
        return f"Generated code based on: {prompt[:100]}"

    @classmethod
    def _narrative_response(cls, prompt: str) -> str:
        return json.dumps({
            "narrative": {
                "opening": "The world stirs with ancient power. Heroes gather at the crossroads of destiny.",
                "acts": [
                    {"name": "Act I: Awakening", "summary": "A hero discovers an ancient artifact that grants mysterious powers."},
                    {"name": "Act II: Rising Conflict", "summary": "The hero faces increasingly powerful foes and discovers allies."},
                    {"name": "Act III: Resolution", "summary": "A final confrontation determines the fate of the world."},
                ],
                "themes": ["destiny", "power", "sacrifice", "friendship"],
                "tone": "epic",
            },
        }, indent=2)

    @classmethod
    def _entity_response(cls, prompt: str) -> str:
        return json.dumps({
            "entities": [
                {"name": "Entity_Alpha", "type": "npc", "position": [100, 50, 0], "components": ["transform", "ai"], "tags": ["friendly"]},
                {"name": "Entity_Beta", "type": "enemy", "position": [-50, 200, 0], "components": ["transform", "combat", "ai"], "tags": ["hostile"]},
                {"name": "Entity_Gamma", "type": "item", "position": [300, 100, 0], "components": ["transform", "inventory"], "tags": ["collectible"]},
            ],
            "status": "created",
        }, indent=2)

    @classmethod
    def _scene_response(cls, prompt: str) -> str:
        return json.dumps({
            "scene": {
                "name": "MainScene",
                "entities": 12,
                "lighting": {"type": "directional", "intensity": 1.0, "color": "#FFF5E0"},
                "camera": {"type": "third_person", "position": [0, 5, 10], "target": [0, 0, 0]},
                "background": {"type": "skybox", "theme": "day"},
                "collision_layers": ["default", "player", "enemy", "item"],
            },
            "status": "active",
        }, indent=2)

    @classmethod
    def _quest_response(cls, prompt: str) -> str:
        return json.dumps({
            "quests": [
                {
                    "id": "quest_001",
                    "title": "The Lost Artifact",
                    "description": "Retrieve the ancient artifact from the forgotten dungeon.",
                    "objectives": [
                        {"type": "reach", "target": "dungeon_entrance", "status": "pending"},
                        {"type": "collect", "target": "artifact", "count": 1, "status": "pending"},
                        {"type": "return", "target": "elder", "status": "pending"},
                    ],
                    "rewards": {"experience": 500, "gold": 100, "item": "Amulet of Power"},
                    "status": "available",
                },
            ],
        }, indent=2)

    @classmethod
    def _npc_response(cls, prompt: str) -> str:
        return json.dumps({
            "npcs": [
                {
                    "name": "Elder Sage",
                    "role": "mentor",
                    "dialogue_tree": {
                        "greeting": "Welcome, young one. The world needs your courage.",
                        "quest_intro": "An ancient artifact has been stolen. Only you can retrieve it.",
                        "farewell": "May fortune guide your path.",
                    },
                    "personality": ["wise", "patient", "mysterious"],
                    "ai_behaviors": ["idle", "greet_player", "offer_quest"],
                },
            ],
        }, indent=2)

    @classmethod
    def _physics_response(cls, prompt: str) -> str:
        return json.dumps({
            "physics": {
                "gravity": [0, -9.81, 0],
                "collision_margin": 0.01,
                "solver_iterations": 8,
                "bounce_threshold": 0.1,
                "sleep_threshold": 0.005,
            },
            "collision_events": [],
            "status": "configured",
        }, indent=2)

    @classmethod
    def _analysis_response(cls, prompt: str) -> str:
        return json.dumps({
            "analysis": {
                "score": 0.82,
                "strengths": [
                    "Clear game loop progression",
                    "Well-structured entity hierarchy",
                    "Good separation of concerns",
                ],
                "weaknesses": [
                    "Limited NPC behavioral variety",
                    "No adaptive difficulty scaling",
                    "Missing performance benchmarks",
                ],
                "recommendations": [
                    "Add behavior tree variants for NPCs",
                    "Implement dynamic difficulty adjustment",
                    "Add performance profiling hooks",
                ],
            },
        }, indent=2)

    @classmethod
    def _fix_response(cls, prompt: str) -> str:
        return json.dumps({
            "diagnosis": {
                "issue": "Identified potential issues in the current implementation",
                "severity": "medium",
                "root_causes": [
                    "Missing null check on entity references",
                    "Race condition in concurrent component updates",
                ],
                "fixes": [
                    {"file": "engine.py", "line": 145, "change": "Add null check before component access"},
                    {"file": "world.py", "line": 89, "change": "Add lock for component update batch"},
                ],
                "verified": True,
            },
        }, indent=2)

    @classmethod
    def _generic_response(cls, prompt: str, temperature: float) -> str:
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
        responses = [
            f"Based on the input, I recommend proceeding with a structured approach. The system has analyzed the request and identified key parameters for execution.",
            f"Analysis complete. The request maps to the game engine's core capabilities. I will proceed with the appropriate tool chain.",
            f"Request received and categorized. The game engine is ready to execute the requested operation with optimal parameters.",
            f"Processing the request through the agent pipeline. Context has been established and the next action has been determined.",
        ]
        idx = seed % len(responses)
        return responses[idx]


class LLMProvider:
    """
    Multi-provider LLM integration supporting OpenAI, Anthropic,
    local models, simulation mode, and custom endpoints.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Any = None
        self._initialized = False

    async def initialize(self) -> bool:
        try:
            provider = self.config.provider.lower()
            if provider == "simulation":
                return await self._init_simulation()
            elif provider == "openai":
                return await self._init_openai()
            elif provider == "anthropic":
                return await self._init_anthropic()
            elif provider == "deepseek":
                return await self._init_deepseek()
            elif provider == "local":
                return await self._init_local()
            elif provider == "ollama":
                return await self._init_ollama()
            else:
                return await self._init_custom()
        except Exception as e:
            print(f"[LLMProvider] Initialization error: {e}")
            return False

    async def generate(self, prompt: str, **kwargs) -> str:
        if not self._initialized:
            await self.initialize()

        provider = self.config.provider.lower()
        try:
            if provider == "simulation":
                return self._generate_simulation(prompt, **kwargs)
            elif provider == "openai":
                return await self._generate_openai(prompt, **kwargs)
            elif provider == "anthropic":
                return await self._generate_anthropic(prompt, **kwargs)
            elif provider == "deepseek":
                return await self._generate_deepseek(prompt, **kwargs)
            elif provider == "local":
                return await self._generate_local(prompt, **kwargs)
            elif provider == "ollama":
                return await self._generate_ollama(prompt, **kwargs)
            else:
                return await self._generate_custom(prompt, **kwargs)
        except Exception as e:
            return f"LLM generation error: {str(e)}"

    async def generate_chat(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        if not self._initialized:
            await self.initialize()

        provider = self.config.provider.lower()
        try:
            if provider == "simulation":
                last_msg = messages[-1]["content"] if messages else ""
                return self._generate_simulation(last_msg, **kwargs)
            elif provider == "openai":
                return await self._chat_openai(messages, **kwargs)
            elif provider == "anthropic":
                return await self._chat_anthropic(messages, **kwargs)
            else:
                return await self._chat_openai(messages, **kwargs)
        except Exception as e:
            return f"LLM chat error: {str(e)}"

    async def _init_simulation(self) -> bool:
        self._client = {"type": "simulation", "engine": SimulationEngine}
        self._initialized = True
        return True

    def _generate_simulation(self, prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", self.config.temperature)
        return SimulationEngine.generate(prompt, temperature)

    async def _init_openai(self) -> bool:
        try:
            import openai
            kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
            self._initialized = True
            return True
        except ImportError:
            print("[LLMProvider] openai package not installed")
            return False

    async def _init_anthropic(self) -> bool:
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.config.api_key)
            self._initialized = True
            return True
        except ImportError:
            print("[LLMProvider] anthropic package not installed")
            return False

    async def _init_deepseek(self) -> bool:
        try:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url or "https://api.deepseek.com/v1",
            )
            self._initialized = True
            return True
        except ImportError:
            print("[LLMProvider] openai package not installed for deepseek")
            return False

    async def _init_ollama(self) -> bool:
        base = self.config.base_url or "http://localhost:11434"
        self._client = {"base_url": base}
        self._initialized = True
        return True

    async def _init_local(self) -> bool:
        self._client = {"type": "local"}
        self._initialized = True
        return True

    async def _init_custom(self) -> bool:
        self._client = {"type": "custom", "base_url": self.config.base_url}
        self._initialized = True
        return True

    async def _generate_openai(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self._chat_openai(messages, **kwargs)

    async def _chat_openai(self, messages: List[Dict], **kwargs) -> str:
        response = await self._client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
        )
        return response.choices[0].message.content

    async def _generate_anthropic(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self._chat_anthropic(messages, **kwargs)

    async def _chat_anthropic(self, messages: List[Dict], **kwargs) -> str:
        response = await self._client.messages.create(
            model=kwargs.get("model", self.config.model),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )
        return response.content[0].text

    async def _generate_deepseek(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self._chat_openai(messages, **kwargs)

    async def _generate_ollama(self, prompt: str, **kwargs) -> str:
        import aiohttp
        base_url = self._client.get("base_url", "http://localhost:11434")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.config.model),
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                    },
                },
            ) as resp:
                data = await resp.json()
                return data.get("response", "")

    async def _generate_local(self, prompt: str, **kwargs) -> str:
        return f"[Local Model] Processed: {prompt[:100]}..."

    async def _generate_custom(self, prompt: str, **kwargs) -> str:
        import aiohttp
        base_url = self._client.get("base_url", "")
        if not base_url:
            return "[Custom] No base URL configured"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": kwargs.get("model", self.config.model),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                },
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            ) as resp:
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def shutdown(self) -> None:
        self._client = None
        self._initialized = False
