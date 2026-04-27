"""
SparkAI Agent - Base Agent Foundation
"""

from __future__ import annotations

import asyncio
import uuid
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field

from sparkai.agent.memory import AgentMemory, MemoryType
from sparkai.agent.toolkit import ToolRegistry, Tool
from sparkai.agent.llm import LLMProvider, LLMConfig


class AgentCapability(Enum):
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    NARRATIVE_GENERATION = "narrative_generation"
    ASSET_GENERATION = "asset_generation"
    WORLD_BUILDING = "world_building"
    GAMEPLAY_DESIGN = "gameplay_design"
    NPC_CONTROL = "npc_control"
    SCENE_MANAGEMENT = "scene_management"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    QUALITY_REVIEW = "quality_review"
    AUDIO_GENERATION = "audio_generation"
    VIDEO_GENERATION = "video_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "agent"
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    assigned_to: str = ""
    status: str = "pending"
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SparkAgent:
    """
    Core Agent class for the SparkLabs AI-Native Game Engine.

    Each agent has:
    - A unique identity (name, role, capabilities)
    - A memory system (short-term, long-term, episodic, semantic)
    - A tool registry for executing actions
    - An LLM provider for reasoning and generation
    - A state machine for lifecycle management
    """

    def __init__(
        self,
        name: str,
        role: str = "general",
        capabilities: Optional[List[AgentCapability]] = None,
        agent_id: Optional[str] = None,
    ):
        self.id = agent_id or str(uuid.uuid4())
        self.name = name
        self.role = role
        self.capabilities = capabilities or [AgentCapability.REASONING]
        self.state = AgentState.IDLE

        self._memory = AgentMemory()
        self._tools = ToolRegistry()
        self._llm: Optional[LLMProvider] = None
        self._message_history: List[AgentMessage] = []
        self._current_task: Optional[AgentTask] = None
        self._task_history: List[AgentTask] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._context: Dict[str, Any] = {}

    @property
    def memory(self) -> AgentMemory:
        return self._memory

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    def set_llm_provider(self, provider: LLMProvider) -> None:
        self._llm = provider

    def add_capability(self, capability: AgentCapability) -> None:
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def has_capability(self, capability: AgentCapability) -> bool:
        return capability in self.capabilities

    def register_tool(self, tool: Tool) -> None:
        self._tools.register(tool)

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def emit(self, event: str, data: Any = None) -> None:
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                handler(data)

    async def think(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Core reasoning method. Uses LLM to process a prompt and return a response.
        """
        self.state = AgentState.THINKING
        self.emit("thinking_start", {"prompt": prompt})

        try:
            memory_context = self._build_memory_context(prompt)

            full_prompt = self._assemble_prompt(prompt, memory_context, context)

            self._memory.remember(
                content=f"User: {prompt}",
                memory_type=MemoryType.SHORT_TERM,
                importance=0.5,
            )

            if self._llm:
                response = await self._llm.generate(full_prompt)
            else:
                response = self._fallback_think(prompt)

            self._memory.remember(
                content=f"Agent({self.name}): {response}",
                memory_type=MemoryType.SHORT_TERM,
                importance=0.6,
            )

            self._message_history.append(
                AgentMessage(role="agent", content=response)
            )

            self.state = AgentState.IDLE
            self.emit("thinking_complete", {"response": response})
            return response

        except Exception as e:
            self.state = AgentState.ERROR
            self.emit("thinking_error", {"error": str(e)})
            return f"Error during thinking: {str(e)}"

    async def act(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute an action using registered tools.
        """
        self.state = AgentState.EXECUTING
        self.emit("action_start", {"action": action, "params": params})

        try:
            tool = self._tools.get(action)
            if tool:
                result = await tool.execute(params or {})
                self._memory.remember(
                    content=f"Executed tool '{action}' with result: {str(result)[:200]}",
                    memory_type=MemoryType.EPISODIC,
                    importance=0.7,
                )
                self.state = AgentState.IDLE
                self.emit("action_complete", {"action": action, "result": result})
                return result
            else:
                self.state = AgentState.IDLE
                return f"Tool '{action}' not found"

        except Exception as e:
            self.state = AgentState.ERROR
            self.emit("action_error", {"action": action, "error": str(e)})
            return f"Error executing action: {str(e)}"

    async def observe(self, observation: str, importance: float = 0.5) -> None:
        """
        Record an observation into memory.
        """
        self._memory.remember(
            content=observation,
            memory_type=MemoryType.SHORT_TERM,
            importance=importance,
        )
        self.emit("observation", {"content": observation})

    async def decide(self, options: List[str], context: Optional[str] = None) -> str:
        """
        Make a decision among given options.
        """
        prompt = f"Choose the best option from the following:\n"
        for i, option in enumerate(options, 1):
            prompt += f"{i}. {option}\n"
        if context:
            prompt += f"\nContext: {context}\n"
        prompt += "\nRespond with only the number of your choice."

        response = await self.think(prompt)
        try:
            choice_idx = int(response.strip()) - 1
            if 0 <= choice_idx < len(options):
                return options[choice_idx]
        except (ValueError, IndexError):
            pass
        return options[0] if options else ""

    def assign_task(self, task: AgentTask) -> None:
        self._current_task = task
        task.status = "in_progress"
        task.assigned_to = self.id
        self.emit("task_assigned", {"task": task})

    async def complete_task(self, result: Any = None) -> None:
        if self._current_task:
            self._current_task.status = "completed"
            self._current_task.result = result
            self._current_task.completed_at = time.time()
            self._task_history.append(self._current_task)
            self.emit("task_completed", {"task": self._current_task})
            self._current_task = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "capabilities": [c.value for c in self.capabilities],
            "current_task": self._current_task.id if self._current_task else None,
            "task_count": len(self._task_history),
            "memory_size": self._memory.size(),
        }

    def _build_memory_context(self, prompt: str) -> str:
        relevant = self._memory.recall(query=prompt, max_results=5)
        if not relevant:
            return ""
        context_parts = ["Relevant memories:"]
        for mem in relevant:
            context_parts.append(f"- {mem['content']}")
        return "\n".join(context_parts)

    def _assemble_prompt(
        self,
        prompt: str,
        memory_context: str,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        parts = [f"You are {self.name}, a {self.role} agent in the SparkLabs AI-Native Game Engine."]
        if self.capabilities:
            caps = ", ".join(c.value for c in self.capabilities)
            parts.append(f"Your capabilities: {caps}")
        if memory_context:
            parts.append(memory_context)
        if extra_context:
            parts.append(f"Additional context: {extra_context}")
        parts.append(f"\nPrompt: {prompt}")
        return "\n".join(parts)

    def _fallback_think(self, prompt: str) -> str:
        return f"[{self.name}] Processed: {prompt[:100]}... (LLM not configured)"
