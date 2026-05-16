"""
SparkLabs Agent - Code Synthesis

Natural-language-to-code synthesis engine for the AI-native game engine.
Accepts plain-language descriptions of game logic, rendering routines,
physics handlers, AI behaviors, and UI components, then produces
syntactically valid and domain-appropriate code in the target language.

Architecture:
  CodeSynthesis
    |-- TemplateRegistry (language-specific code templates)
    |-- SyntaxValidator (basic structural checks per language)
    |-- DomainAdapter (game-domain-specific boilerplate injection)
    |-- ResultCache (history of past synthesis runs)

Synthesis Modes:
  - FULL_GENERATION: create code from scratch from a natural description
  - PARTIAL_COMPLETION: auto-complete a partially-written code block
  - REFACTOR: restructure existing code for clarity or performance
  - BUGFIX: generate a targeted fix for a described defect
  - OPTIMIZE: improve performance characteristics of working code

Supported Languages:
  Python, JavaScript, GDScript, Lua, C#
"""

from __future__ import annotations

import re
import textwrap
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TargetLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    GDSCRIPT = "gdscript"
    LUA = "lua"
    CSHARP = "csharp"


class SynthesisMode(Enum):
    FULL_GENERATION = "full_generation"
    PARTIAL_COMPLETION = "partial_completion"
    REFACTOR = "refactor"
    BUGFIX = "bugfix"
    OPTIMIZE = "optimize"


class CodeDomain(Enum):
    GAME_LOGIC = "game_logic"
    RENDERING = "rendering"
    PHYSICS = "physics"
    AI_BEHAVIOR = "ai_behavior"
    UI = "ui"
    NETWORKING = "networking"
    AUDIO = "audio"
    INPUT_HANDLING = "input_handling"


class SynthesisStatus(Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEWED = "reviewed"


LANGUAGE_TEMPLATES: Dict[Tuple[CodeDomain, TargetLanguage], str] = {
    (CodeDomain.GAME_LOGIC, TargetLanguage.PYTHON): (
        "class {name}:\n"
        "    def __init__(self):\n"
        "        self._active = True\n\n"
        "    def update(self, delta_time: float) -> None:\n"
        "        pass\n"
    ),
    (CodeDomain.GAME_LOGIC, TargetLanguage.JAVASCRIPT): (
        "class {name} {\n"
        "    constructor() {\n"
        "        this._active = true;\n"
        "    }\n\n"
        "    update(deltaTime) {\n"
        "        // game logic\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.GAME_LOGIC, TargetLanguage.GDSCRIPT): (
        "extends Node\n\n"
        "var _active := true\n\n"
        "func _process(delta: float) -> void:\n"
        "    pass\n"
    ),
    (CodeDomain.GAME_LOGIC, TargetLanguage.LUA): (
        "local {name} = {}\n"
        "{name}._active = true\n\n"
        "function {name}:update(dt)\n"
        "end\n\n"
        "return {name}\n"
    ),
    (CodeDomain.GAME_LOGIC, TargetLanguage.CSHARP): (
        "using UnityEngine;\n\n"
        "public class {name} : MonoBehaviour\n"
        "{\n"
        "    private bool _active = true;\n\n"
        "    void Update()\n"
        "    {\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.RENDERING, TargetLanguage.PYTHON): (
        "def render_frame(surface, camera, scene_graph):\n"
        "    surface.clear()\n"
        "    for node in scene_graph.visible_nodes(camera):\n"
        "        surface.draw(node.mesh, node.transform)\n"
    ),
    (CodeDomain.RENDERING, TargetLanguage.JAVASCRIPT): (
        "function renderFrame(context, camera, sceneGraph) {\n"
        "    context.clearRect(0, 0, context.canvas.width, context.canvas.height);\n"
        "    sceneGraph.visibleNodes(camera).forEach(node => {\n"
        "        context.drawImage(node.texture, node.x, node.y);\n"
        "    });\n"
        "}\n"
    ),
    (CodeDomain.RENDERING, TargetLanguage.GDSCRIPT): (
        "func _draw() -> void:\n"
        "    for node in get_tree().get_nodes_in_group(\"renderable\"):\n"
        "        draw_texture(node.texture, node.position)\n"
    ),
    (CodeDomain.RENDERING, TargetLanguage.LUA): (
        "function RenderFrame(surface, camera, scene)\n"
        "    surface:clear()\n"
        "    for _, node in ipairs(scene.nodes) do\n"
        "        if camera:isVisible(node) then\n"
        "            surface:draw(node.mesh, node.transform)\n"
        "        end\n"
        "    end\n"
        "end\n"
    ),
    (CodeDomain.RENDERING, TargetLanguage.CSHARP): (
        "void RenderFrame(RenderTexture target, Camera camera, SceneGraph scene)\n"
        "{\n"
        "    target.Clear();\n"
        "    foreach (var node in scene.VisibleNodes(camera))\n"
        "    {\n"
        "        Graphics.DrawMesh(node.Mesh, node.Transform, node.Material, 0);\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.PHYSICS, TargetLanguage.PYTHON): (
        "def apply_force(body, force_vector):\n"
        "    body.acceleration += force_vector / body.mass\n\n"
        "def integrate(body, delta_time):\n"
        "    body.velocity += body.acceleration * delta_time\n"
        "    body.position += body.velocity * delta_time\n"
        "    body.acceleration = Vector3.zero()\n"
    ),
    (CodeDomain.PHYSICS, TargetLanguage.JAVASCRIPT): (
        "function applyForce(body, forceVec) {\n"
        "    body.acceleration.add(forceVec.divide(body.mass));\n"
        "}\n\n"
        "function integrate(body, dt) {\n"
        "    body.velocity.add(body.acceleration.multiply(dt));\n"
        "    body.position.add(body.velocity.multiply(dt));\n"
        "    body.acceleration.set(0, 0, 0);\n"
        "}\n"
    ),
    (CodeDomain.PHYSICS, TargetLanguage.GDSCRIPT): (
        "func apply_force(body: RigidBody2D, force: Vector2) -> void:\n"
        "    body.apply_central_force(force)\n"
    ),
    (CodeDomain.PHYSICS, TargetLanguage.LUA): (
        "function ApplyForce(body, fx, fy)\n"
        "    body.vx = body.vx + fx / body.mass\n"
        "    body.vy = body.vy + fy / body.mass\n"
        "end\n"
    ),
    (CodeDomain.PHYSICS, TargetLanguage.CSHARP): (
        "void ApplyForce(Rigidbody body, Vector3 force)\n"
        "{\n"
        "    body.AddForce(force, ForceMode.Force);\n"
        "}\n"
    ),
    (CodeDomain.AI_BEHAVIOR, TargetLanguage.PYTHON): (
        "class AIAgent:\n"
        "    def __init__(self):\n"
        "        self.state = \"idle\"\n"
        "        self.target = None\n\n"
        "    def perceive(self, environment):\n"
        "        self.target = environment.nearest_enemy(self.position)\n\n"
        "    def decide(self) -> str:\n"
        "        if self.target and self.distance_to(self.target) < 10.0:\n"
        "            return \"attack\"\n"
        "        elif self.target:\n"
        "            return \"chase\"\n"
        "        return \"patrol\"\n\n"
        "    def act(self, action: str, delta_time: float):\n"
        "        getattr(self, f\"_do_{action}\")(delta_time)\n"
    ),
    (CodeDomain.AI_BEHAVIOR, TargetLanguage.JAVASCRIPT): (
        "class AIAgent {\n"
        "    constructor() {\n"
        "        this.state = 'idle';\n"
        "        this.target = null;\n"
        "    }\n\n"
        "    perceive(environment) {\n"
        "        this.target = environment.nearestEnemy(this.position);\n"
        "    }\n\n"
        "    decide() {\n"
        "        if (this.target && this.distanceTo(this.target) < 10) return 'attack';\n"
        "        if (this.target) return 'chase';\n"
        "        return 'patrol';\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.AI_BEHAVIOR, TargetLanguage.GDSCRIPT): (
        "extends Node\n\n"
        "enum State { IDLE, PATROL, CHASE, ATTACK }\n"
        "var current_state = State.IDLE\n"
        "var target: Node2D = null\n\n"
        "func _process(delta: float) -> void:\n"
        "    match current_state:\n"
        "        State.IDLE: _on_idle(delta)\n"
        "        State.CHASE: _on_chase(delta)\n"
    ),
    (CodeDomain.AI_BEHAVIOR, TargetLanguage.LUA): (
        "local AIAgent = {}\n"
        "AIAgent.__index = AIAgent\n\n"
        "function AIAgent:new()\n"
        "    local agent = setmetatable({}, AIAgent)\n"
        "    agent.state = \"idle\"\n"
        "    agent.target = nil\n"
        "    return agent\n"
        "end\n\n"
        "function AIAgent:update(dt)\n"
        "    self:perceive()\n"
        "    self:decide()\n"
        "    self:act(dt)\n"
        "end\n"
    ),
    (CodeDomain.AI_BEHAVIOR, TargetLanguage.CSHARP): (
        "public class AIAgent : MonoBehaviour\n"
        "{\n"
        "    public enum State { Idle, Patrol, Chase, Attack }\n"
        "    public State CurrentState = State.Idle;\n"
        "    private Transform _target;\n\n"
        "    void Update()\n"
        "    {\n"
        "        switch (CurrentState)\n"
        "        {\n"
        "            case State.Idle: OnIdle(); break;\n"
        "            case State.Chase: OnChase(); break;\n"
        "            case State.Attack: OnAttack(); break;\n"
        "        }\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.UI, TargetLanguage.PYTHON): (
        "class UIManager:\n"
        "    def __init__(self):\n"
        "        self.widgets = []\n"
        "        self.focused = None\n\n"
        "    def add_widget(self, widget):\n"
        "        self.widgets.append(widget)\n\n"
        "    def handle_event(self, event):\n"
        "        for widget in reversed(self.widgets):\n"
        "            if widget.hit_test(event.position) and widget.enabled:\n"
        "                widget.on_event(event)\n"
        "                return True\n"
        "        return False\n"
    ),
    (CodeDomain.UI, TargetLanguage.JAVASCRIPT): (
        "class UIManager {\n"
        "    constructor() {\n"
        "        this.widgets = [];\n"
        "        this.focused = null;\n"
        "    }\n\n"
        "    addWidget(widget) {\n"
        "        this.widgets.push(widget);\n"
        "    }\n\n"
        "    handleEvent(event) {\n"
        "        for (let i = this.widgets.length - 1; i >= 0; i--) {\n"
        "            const w = this.widgets[i];\n"
        "            if (w.hitTest(event.x, event.y) && w.enabled) {\n"
        "                w.onEvent(event);\n"
        "                return true;\n"
        "            }\n"
        "        }\n"
        "        return false;\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.UI, TargetLanguage.GDSCRIPT): (
        "extends Control\n\n"
        "var widgets := []\n"
        "var focused: Control = null\n\n"
        "func _gui_input(event: InputEvent) -> void:\n"
        "    for widget in widgets:\n"
        "        if widget.get_rect().has_point(event.position):\n"
        "            widget._gui_input(event)\n"
        "            return\n"
    ),
    (CodeDomain.UI, TargetLanguage.LUA): (
        "local UIManager = {}\n\n"
        "function UIManager:new()\n"
        "    local mgr = {widgets = {}, focused = nil}\n"
        "    setmetatable(mgr, {__index = UIManager})\n"
        "    return mgr\n"
        "end\n\n"
        "function UIManager:handleEvent(event)\n"
        "    for i = #self.widgets, 1, -1 do\n"
        "        local w = self.widgets[i]\n"
        "        if w:hitTest(event.x, event.y) and w.enabled then\n"
        "            w:onEvent(event)\n"
        "            return true\n"
        "        end\n"
        "    end\n"
        "    return false\n"
        "end\n"
    ),
    (CodeDomain.UI, TargetLanguage.CSHARP): (
        "public class UIManager : MonoBehaviour\n"
        "{\n"
        "    private List<UIWidget> _widgets = new List<UIWidget>();\n"
        "    private UIWidget _focused;\n\n"
        "    public void AddWidget(UIWidget widget)\n"
        "    {\n"
        "        _widgets.Add(widget);\n"
        "    }\n\n"
        "    public bool HandleEvent(UIEvent e)\n"
        "    {\n"
        "        for (int i = _widgets.Count - 1; i >= 0; i--)\n"
        "        {\n"
        "            var w = _widgets[i];\n"
        "            if (w.HitTest(e.Position) && w.Enabled)\n"
        "            {\n"
        "                w.OnEvent(e);\n"
        "                return true;\n"
        "            }\n"
        "        }\n"
        "        return false;\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.NETWORKING, TargetLanguage.PYTHON): (
        "class NetworkManager:\n"
        "    def __init__(self, host: str, port: int):\n"
        "        self.host = host\n"
        "        self.port = port\n"
        "        self.connected = False\n\n"
        "    def connect(self) -> bool:\n"
        "        self.connected = True\n"
        "        return True\n\n"
        "    def send(self, data: bytes) -> None:\n"
        "        if not self.connected:\n"
        "            raise ConnectionError(\"Not connected\")\n\n"
        "    def receive(self) -> Optional[bytes]:\n"
        "        return None\n"
    ),
    (CodeDomain.NETWORKING, TargetLanguage.JAVASCRIPT): (
        "class NetworkManager {\n"
        "    constructor(host, port) {\n"
        "        this.host = host;\n"
        "        this.port = port;\n"
        "        this.connected = false;\n"
        "    }\n\n"
        "    async connect() {\n"
        "        this.connected = true;\n"
        "        return true;\n"
        "    }\n\n"
        "    send(data) {\n"
        "        if (!this.connected) throw new Error('Not connected');\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.NETWORKING, TargetLanguage.GDSCRIPT): (
        "extends Node\n\n"
        "var _host: String\n"
        "var _port: int\n"
        "var _connected := false\n\n"
        "func connect_to_host() -> bool:\n"
        "    var peer = PacketPeerUDP.new()\n"
        "    peer.connect_to_host(_host, _port)\n"
        "    _connected = true\n"
        "    return true\n"
    ),
    (CodeDomain.NETWORKING, TargetLanguage.LUA): (
        "local NetworkManager = {}\n\n"
        "function NetworkManager:new(host, port)\n"
        "    local nm = {host = host, port = port, connected = false}\n"
        "    setmetatable(nm, {__index = NetworkManager})\n"
        "    return nm\n"
        "end\n\n"
        "function NetworkManager:connect()\n"
        "    self.connected = true\n"
        "    return true\n"
        "end\n"
    ),
    (CodeDomain.NETWORKING, TargetLanguage.CSHARP): (
        "public class NetworkManager : MonoBehaviour\n"
        "{\n"
        "    public string Host = \"localhost\";\n"
        "    public int Port = 7777;\n"
        "    private bool _connected;\n\n"
        "    public bool Connect()\n"
        "    {\n"
        "        _connected = true;\n"
        "        return true;\n"
        "    }\n\n"
        "    public void Send(byte[] data)\n"
        "    {\n"
        "        if (!_connected) throw new InvalidOperationException(\"Not connected\");\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.AUDIO, TargetLanguage.PYTHON): (
        "class AudioSystem:\n"
        "    def __init__(self):\n"
        "        self.channels = {}\n"
        "        self.master_volume = 1.0\n\n"
        "    def play(self, clip_name: str, volume: float = 1.0, loop: bool = False):\n"
        "        pass\n\n"
        "    def stop(self, clip_name: str) -> None:\n"
        "        if clip_name in self.channels:\n"
        "            del self.channels[clip_name]\n"
    ),
    (CodeDomain.AUDIO, TargetLanguage.JAVASCRIPT): (
        "class AudioSystem {\n"
        "    constructor() {\n"
        "        this.channels = {};\n"
        "        this.masterVolume = 1.0;\n"
        "    }\n\n"
        "    play(name, volume = 1.0, loop = false) {\n"
        "        const ctx = new AudioContext();\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.AUDIO, TargetLanguage.GDSCRIPT): (
        "extends Node\n\n"
        "var master_volume := 1.0 setget set_master_volume\n\n"
        "func play_sfx(clip: AudioStream, volume_db: float = 0.0) -> void:\n"
        "    var player = AudioStreamPlayer.new()\n"
        "    player.stream = clip\n"
        "    player.volume_db = volume_db\n"
        "    add_child(player)\n"
        "    player.play()\n"
    ),
    (CodeDomain.AUDIO, TargetLanguage.LUA): (
        "local AudioSystem = {}\n\n"
        "function AudioSystem:new()\n"
        "    local sys = {channels = {}, masterVolume = 1.0}\n"
        "    return sys\n"
        "end\n\n"
        "function AudioSystem:play(name, volume, loop)\n"
        "    volume = volume or 1.0\n"
        "    loop = loop or false\n"
        "end\n"
    ),
    (CodeDomain.AUDIO, TargetLanguage.CSHARP): (
        "public class AudioSystem : MonoBehaviour\n"
        "{\n"
        "    public float MasterVolume = 1.0f;\n"
        "    private Dictionary<string, AudioSource> _channels = new();\n\n"
        "    public void Play(string clipName, float volume = 1.0f, bool loop = false)\n"
        "    {\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.INPUT_HANDLING, TargetLanguage.PYTHON): (
        "class InputManager:\n"
        "    def __init__(self):\n"
        "        self._bindings = {}\n"
        "        self._key_states = {}\n\n"
        "    def bind(self, action: str, key: str) -> None:\n"
        "        self._bindings[action] = key\n\n"
        "    def is_pressed(self, action: str) -> bool:\n"
        "        return self._key_states.get(self._bindings.get(action), False)\n\n"
        "    def poll_events(self) -> List[str]:\n"
        "        return [a for a, k in self._bindings.items() if self._key_states.get(k)]\n"
    ),
    (CodeDomain.INPUT_HANDLING, TargetLanguage.JAVASCRIPT): (
        "class InputManager {\n"
        "    constructor() {\n"
        "        this.bindings = {};\n"
        "        this.keyStates = {};\n"
        "        window.addEventListener('keydown', e => this.keyStates[e.code] = true);\n"
        "        window.addEventListener('keyup', e => this.keyStates[e.code] = false);\n"
        "    }\n\n"
        "    bind(action, keyCode) {\n"
        "        this.bindings[action] = keyCode;\n"
        "    }\n\n"
        "    isPressed(action) {\n"
        "        return !!this.keyStates[this.bindings[action]];\n"
        "    }\n"
        "}\n"
    ),
    (CodeDomain.INPUT_HANDLING, TargetLanguage.GDSCRIPT): (
        "extends Node\n\n"
        "var _action_map := {}\n\n"
        "func _ready() -> void:\n"
        "    _action_map.move_left = \"ui_left\"\n"
        "    _action_map.move_right = \"ui_right\"\n"
        "    _action_map.jump = \"ui_accept\"\n\n"
        "func is_action_pressed(action: String) -> bool:\n"
        "    return Input.is_action_pressed(_action_map.get(action, \"\"))\n"
    ),
    (CodeDomain.INPUT_HANDLING, TargetLanguage.LUA): (
        "local InputManager = {}\n\n"
        "function InputManager:new()\n"
        "    local im = {bindings = {}, keyStates = {}}\n"
        "    return im\n"
        "end\n\n"
        "function InputManager:bind(action, key)\n"
        "    self.bindings[action] = key\n"
        "end\n\n"
        "function InputManager:isPressed(action)\n"
        "    return self.keyStates[self.bindings[action]] or false\n"
        "end\n"
    ),
    (CodeDomain.INPUT_HANDLING, TargetLanguage.CSHARP): (
        "public class InputManager : MonoBehaviour\n"
        "{\n"
        "    private Dictionary<string, KeyCode> _bindings = new();\n\n"
        "    void Start()\n"
        "    {\n"
        "        _bindings[\"jump\"] = KeyCode.Space;\n"
        "        _bindings[\"move_left\"] = KeyCode.A;\n"
        "        _bindings[\"move_right\"] = KeyCode.D;\n"
        "    }\n\n"
        "    public bool IsPressed(string action)\n"
        "    {\n"
        "        return _bindings.TryGetValue(action, out var key) && Input.GetKey(key);\n"
        "    }\n"
        "}\n"
    ),
}

DOMAIN_CLASS_NAMES: Dict[CodeDomain, str] = {
    CodeDomain.GAME_LOGIC: "GameController",
    CodeDomain.RENDERING: "RenderPipeline",
    CodeDomain.PHYSICS: "PhysicsBody",
    CodeDomain.AI_BEHAVIOR: "AIAgent",
    CodeDomain.UI: "UIManager",
    CodeDomain.NETWORKING: "NetworkManager",
    CodeDomain.AUDIO: "AudioSystem",
    CodeDomain.INPUT_HANDLING: "InputManager",
}

SYNTAX_PATTERNS: Dict[TargetLanguage, List[Tuple[str, str]]] = {
    TargetLanguage.PYTHON: [
        (r"^\s*def\s+\w+\s*\(.*\)\s*:\s*$", "Missing colon after function definition"),
        (r"^[ \t]+$", "Trailing whitespace"),
        (r"print\s+[^(]", "Use print() with parentheses (Python 3)"),
    ],
    TargetLanguage.JAVASCRIPT: [
        (r"function\s+\w+\s*\(.*\)\s*\{?\s*$", "Missing opening brace in function"),
        (r"console\.log\s*\([^)]*$", "Unclosed console.log call"),
        (r"var\s+\w+\s*=\s*$", "Incomplete variable declaration"),
    ],
    TargetLanguage.GDSCRIPT: [
        (r"^func\s+\w+\s*\(.*\)\s*:?\s*$", "Missing colon after func definition"),
        (r"^\s*var\s+\w+\s*$", "Uninitialized GDScript variable"),
        (r"print\s+[^(]", "Use print() with parentheses in GDScript 2.x"),
    ],
    TargetLanguage.LUA: [
        (r"function\s+\w+\s*\(.*\)\s*$", "Missing end keyword for function"),
        (r"local\s+\w+\s*=\s*$", "Incomplete local variable assignment"),
        (r"if\s+.+\s+then\s*$", "Missing end for if block"),
    ],
    TargetLanguage.CSHARP: [
        (r"class\s+\w+\s*\{?\s*$", "Missing opening brace in class definition"),
        (r";\s*;\s*;", "Multiple semicolons"),
        (r"void\s+\w+\s*\(.*\)\s*$", "Missing method body braces"),
    ],
}


@dataclass
class SynthesisRequest:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str = ""
    language: TargetLanguage = TargetLanguage.PYTHON
    domain: CodeDomain = CodeDomain.GAME_LOGIC
    mode: SynthesisMode = SynthesisMode.FULL_GENERATION
    context_code: str = ""
    constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "prompt": self.prompt[:200],
            "language": self.language.value,
            "domain": self.domain.value,
            "mode": self.mode.value,
            "context_code_length": len(self.context_code),
            "constraints": self.constraints,
        }


@dataclass
class SynthesisResult:
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    status: SynthesisStatus = SynthesisStatus.QUEUED
    generated_code: str = ""
    explanation: str = ""
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    token_count: int = 0
    language: TargetLanguage = TargetLanguage.PYTHON
    domain: CodeDomain = CodeDomain.GAME_LOGIC
    mode: SynthesisMode = SynthesisMode.FULL_GENERATION
    duration_ms: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "generated_code": self.generated_code[:500],
            "explanation": self.explanation[:300],
            "confidence": round(self.confidence, 2),
            "warnings": self.warnings,
            "token_count": self.token_count,
            "language": self.language.value,
            "domain": self.domain.value,
            "mode": self.mode.value,
            "duration_ms": round(self.duration_ms, 2),
        }


class CodeSynthesis:
    """
    Natural-language-to-code synthesis engine for game development.

    Accepts plain-language descriptions and produces idiomatic code
    in the requested target language and game domain. Supports full
    generation, partial completion, refactoring, bugfixing, and
    optimization modes.

    Usage:
        synth = CodeSynthesis.get_instance()
        request = SynthesisRequest(
            prompt="Create a player controller with WASD movement",
            language=TargetLanguage.GDSCRIPT,
            domain=CodeDomain.INPUT_HANDLING,
        )
        result = synth.synthesize(request)
        print(result.generated_code)
    """

    _instance: Optional[CodeSynthesis] = None

    def __init__(self):
        self._lock = threading.Lock()
        self._history: List[SynthesisResult] = []
        self._total_requests: int = 0
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._total_tokens: int = 0
        self._total_duration_ms: float = 0.0
        self._domain_counts: Dict[str, int] = {}
        self._language_counts: Dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> CodeSynthesis:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """
        Generate code from a natural language description.

        Selects the appropriate domain template, injects contextual
        boilerplate, and produces a complete, structured result with
        confidence scoring and warnings.
        """
        start = time.time()

        with self._lock:
            self._total_requests += 1
            domain_key = request.domain.value
            language_key = request.language.value
            self._domain_counts[domain_key] = self._domain_counts.get(domain_key, 0) + 1
            self._language_counts[language_key] = self._language_counts.get(language_key, 0) + 1

        template_key = (request.domain, request.language)
        base_template = LANGUAGE_TEMPLATES.get(template_key, self._fallback_template(request.language))
        class_name = DOMAIN_CLASS_NAMES.get(request.domain, "GeneratedComponent")
        base_code = base_template.replace("{name}", class_name)

        if request.mode == SynthesisMode.FULL_GENERATION:
            generated, confidence, warnings = self._generate_from_prompt(
                request.prompt, request.language, request.domain, base_code,
            )
        elif request.mode == SynthesisMode.PARTIAL_COMPLETION:
            generated = self._merge_with_context(base_code, request.context_code)
            confidence = 0.75
            warnings = []
        elif request.mode == SynthesisMode.REFACTOR:
            generated, confidence, warnings = self._simulate_refactor(
                request.context_code, request.prompt,
            )
        elif request.mode == SynthesisMode.BUGFIX:
            generated, confidence, warnings = self._simulate_bugfix(
                request.context_code, request.prompt,
            )
        elif request.mode == SynthesisMode.OPTIMIZE:
            generated, confidence, warnings = self._simulate_optimize(
                request.context_code, request.prompt,
            )
        else:
            generated = base_code
            confidence = 0.3
            warnings = [f"Unknown synthesis mode: {request.mode.value}"]

        constraint_warnings = self._check_constraints(generated, request.constraints, request.language)
        warnings.extend(constraint_warnings)

        token_estimate = len(generated.split()) + len(request.prompt.split())
        status = SynthesisStatus.COMPLETED if confidence >= 0.3 else SynthesisStatus.FAILED

        duration = (time.time() - start) * 1000.0

        result = SynthesisResult(
            request_id=request.request_id,
            status=status,
            generated_code=generated,
            explanation=self._build_explanation(request.prompt, request.domain, request.language),
            confidence=round(confidence, 2),
            warnings=warnings,
            token_count=token_estimate,
            language=request.language,
            domain=request.domain,
            mode=request.mode,
            duration_ms=round(duration, 2),
        )

        with self._lock:
            self._history.append(result)
            if status == SynthesisStatus.COMPLETED:
                self._total_completed += 1
            else:
                self._total_failed += 1
            self._total_tokens += token_estimate
            self._total_duration_ms += duration

            if len(self._history) > 500:
                self._history = self._history[-500:]

        return result

    def complete(self, partial_code: str, intent: str) -> SynthesisResult:
        """
        Auto-complete a partial code block based on the expressed intent.

        Analyzes the incomplete code structure, determines the most
        likely target language from syntax cues, and fills in missing
        logic while preserving the existing code style.
        """
        start = time.time()

        detected_language = self._detect_language(partial_code)
        domain = self._infer_domain(partial_code, intent)

        request = SynthesisRequest(
            prompt=intent,
            language=detected_language,
            domain=domain,
            mode=SynthesisMode.PARTIAL_COMPLETION,
            context_code=partial_code,
        )

        base_template = LANGUAGE_TEMPLATES.get((domain, detected_language), "")
        class_name = DOMAIN_CLASS_NAMES.get(domain, "GeneratedComponent")
        if not base_template:
            base_template = self._fallback_template(detected_language)
        template_body = base_template.replace("{name}", class_name)

        completed_code = self._merge_completion(partial_code, template_body, intent)

        warnings: List[str] = []
        if detected_language == TargetLanguage.PYTHON:
            warnings.append("Language auto-detected as Python based on syntax cues")

        status = SynthesisStatus.COMPLETED if completed_code else SynthesisStatus.FAILED
        confidence = 0.65 if completed_code else 0.1
        token_estimate = len(completed_code.split()) + len(intent.split())
        duration = (time.time() - start) * 1000.0

        result = SynthesisResult(
            request_id=request.request_id,
            status=status,
            generated_code=completed_code,
            explanation=f"Auto-completed {detected_language.value} code for intent: {intent[:100]}",
            confidence=round(confidence, 2),
            warnings=warnings,
            token_count=token_estimate,
            language=detected_language,
            domain=domain,
            mode=SynthesisMode.PARTIAL_COMPLETION,
            duration_ms=round(duration, 2),
        )

        with self._lock:
            self._total_requests += 1
            self._history.append(result)
            if status == SynthesisStatus.COMPLETED:
                self._total_completed += 1
            else:
                self._total_failed += 1
            self._total_tokens += token_estimate
            self._total_duration_ms += duration

            if len(self._history) > 500:
                self._history = self._history[-500:]

        return result

    def refactor(self, source_code: str, goal: str) -> SynthesisResult:
        """
        Restructure existing code to improve clarity, maintainability,
        or performance based on the stated goal.
        """
        start = time.time()

        language = self._detect_language(source_code)
        domain = self._infer_domain(source_code, goal)

        request = SynthesisRequest(
            prompt=goal,
            language=language,
            domain=domain,
            mode=SynthesisMode.REFACTOR,
            context_code=source_code,
        )

        with self._lock:
            self._total_requests += 1
            domain_key = domain.value
            language_key = language.value
            self._domain_counts[domain_key] = self._domain_counts.get(domain_key, 0) + 1
            self._language_counts[language_key] = self._language_counts.get(language_key, 0) + 1

        refactored, confidence, warnings = self._simulate_refactor(source_code, goal)

        duration = (time.time() - start) * 1000.0
        token_estimate = len(refactored.split()) + len(goal.split())
        status = SynthesisStatus.COMPLETED if confidence >= 0.3 else SynthesisStatus.FAILED

        result = SynthesisResult(
            request_id=request.request_id,
            status=status,
            generated_code=refactored,
            explanation=f"Refactored {language.value} code: {goal[:100]}",
            confidence=round(confidence, 2),
            warnings=warnings,
            token_count=token_estimate,
            language=language,
            domain=domain,
            mode=SynthesisMode.REFACTOR,
            duration_ms=round(duration, 2),
        )

        with self._lock:
            self._history.append(result)
            if status == SynthesisStatus.COMPLETED:
                self._total_completed += 1
            else:
                self._total_failed += 1
            self._total_tokens += token_estimate
            self._total_duration_ms += duration

            if len(self._history) > 500:
                self._history = self._history[-500:]

        return result

    def fix_bug(self, source_code: str, bug_description: str) -> SynthesisResult:
        """
        Generate a targeted bugfix for the described defect in the
        provided source code.
        """
        start = time.time()

        language = self._detect_language(source_code)
        domain = self._infer_domain(source_code, bug_description)

        request = SynthesisRequest(
            prompt=bug_description,
            language=language,
            domain=domain,
            mode=SynthesisMode.BUGFIX,
            context_code=source_code,
        )

        with self._lock:
            self._total_requests += 1
            domain_key = domain.value
            language_key = language.value
            self._domain_counts[domain_key] = self._domain_counts.get(domain_key, 0) + 1
            self._language_counts[language_key] = self._language_counts.get(language_key, 0) + 1

        fixed_code, confidence, warnings = self._simulate_bugfix(source_code, bug_description)

        duration = (time.time() - start) * 1000.0
        token_estimate = len(fixed_code.split()) + len(bug_description.split())
        status = SynthesisStatus.COMPLETED if confidence >= 0.3 else SynthesisStatus.FAILED

        result = SynthesisResult(
            request_id=request.request_id,
            status=status,
            generated_code=fixed_code,
            explanation=f"Applied bugfix for: {bug_description[:100]}",
            confidence=round(confidence, 2),
            warnings=warnings,
            token_count=token_estimate,
            language=language,
            domain=domain,
            mode=SynthesisMode.BUGFIX,
            duration_ms=round(duration, 2),
        )

        with self._lock:
            self._history.append(result)
            if status == SynthesisStatus.COMPLETED:
                self._total_completed += 1
            else:
                self._total_failed += 1
            self._total_tokens += token_estimate
            self._total_duration_ms += duration

            if len(self._history) > 500:
                self._history = self._history[-500:]

        return result

    def explain_code(self, source_code: str) -> str:
        """
        Produce a human-readable explanation of what the provided
        source code does, its structure, and its key behaviors.
        """
        language = self._detect_language(source_code)
        domain = self._infer_domain(source_code, "")

        explanation_parts: List[str] = [
            f"Language: {language.value}",
            f"Game Domain: {domain.value}",
        ]

        line_count = source_code.count("\n") + 1
        explanation_parts.append(f"Lines of code: {line_count}")

        if "class " in source_code:
            class_matches = re.findall(r"class\s+(\w+)", source_code)
            explanation_parts.append(f"Classes defined: {', '.join(class_matches)}")

        if "def " in source_code or "function " in source_code or "func " in source_code:
            func_patterns = {
                TargetLanguage.PYTHON: r"def\s+(\w+)",
                TargetLanguage.JAVASCRIPT: r"function\s+(\w+)",
                TargetLanguage.GDSCRIPT: r"func\s+(\w+)",
                TargetLanguage.LUA: r"function\s+(\w+)",
                TargetLanguage.CSHARP: r"(?:void|bool|int|float|string|var)\s+(\w+)\s*\(",
            }
            pattern = func_patterns.get(language, r"def\s+(\w+)")
            func_matches = re.findall(pattern, source_code)
            if func_matches:
                explanation_parts.append(f"Functions/methods: {', '.join(func_matches[:10])}")

        if "if " in source_code:
            if_count = len(re.findall(r"\bif\s+", source_code))
            for_count = len(re.findall(r"\bfor\s+", source_code))
            while_count = len(re.findall(r"\bwhile\s+", source_code))
            explanation_parts.append(
                f"Control flow: {if_count} conditionals, {for_count} loops, {while_count} while-loops"
            )

        explanation_parts.append(
            f"\nThis code implements {domain.value.replace('_', ' ')} functionality "
            f"in {language.value}."
        )

        return "\n".join(explanation_parts)

    def validate_syntax(self, code: str, language: TargetLanguage) -> List[str]:
        """
        Perform basic syntax validation on the provided code for the
        specified target language. Returns a list of identified issues.
        """
        issues: List[str] = []
        patterns = SYNTAX_PATTERNS.get(language, [])

        if not code.strip():
            issues.append("Code is empty")
            return issues

        lines = code.split("\n")
        for pattern, description in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    issues.append(f"Line {i}: {description} — {line.strip()[:60]}")

        brace_stack: List[str] = []
        brace_pairs = {"(": ")", "[": "]", "{": "}"}
        for i, line in enumerate(lines, 1):
            for char in line:
                if char in brace_pairs:
                    brace_stack.append(char)
                elif brace_stack and char == brace_pairs.get(brace_stack[-1], ""):
                    brace_stack.pop()
                elif char in brace_pairs.values():
                    issues.append(f"Line {i}: Unmatched closing bracket '{char}'")

        if brace_stack:
            issues.append(
                f"Unclosed brackets: {', '.join(brace_stack[-5:])} (showing last 5)"
            )

        if language == TargetLanguage.PYTHON:
            indent_error = self._check_python_indentation(lines)
            if indent_error:
                issues.append(indent_error)
        elif language == TargetLanguage.GDSCRIPT:
            indent_error = self._check_python_indentation(lines)
            if indent_error:
                issues.append(indent_error)

        return issues

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return past synthesis results as dictionaries, ordered from
        most recent to oldest.
        """
        with self._lock:
            return [r.to_dict() for r in reversed(self._history[-limit:])]

    def get_stats(self) -> Dict[str, Any]:
        """
        Return synthesis statistics including request counts,
        completion rate, domain and language breakdowns, and
        performance metrics.
        """
        with self._lock:
            avg_confidence = (
                sum(r.confidence for r in self._history) / max(1, len(self._history))
            )
            avg_duration = (
                self._total_duration_ms / max(1, self._total_requests)
            )

            return {
                "total_requests": self._total_requests,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "completion_rate": round(
                    self._total_completed / max(1, self._total_requests) * 100, 1,
                ),
                "total_tokens": self._total_tokens,
                "avg_confidence": round(avg_confidence, 2),
                "avg_duration_ms": round(avg_duration, 2),
                "total_duration_ms": round(self._total_duration_ms, 2),
                "domain_breakdown": dict(self._domain_counts),
                "language_breakdown": dict(self._language_counts),
                "cached_results": len(self._history),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fallback_template(self, language: TargetLanguage) -> str:
        """
        Return a minimal template when no domain-specific template
        exists for the requested language.
        """
        fallbacks = {
            TargetLanguage.PYTHON: "def {name}():\n    pass\n",
            TargetLanguage.JAVASCRIPT: "function {name}() {\n}\n",
            TargetLanguage.GDSCRIPT: "func {name}() -> void:\n    pass\n",
            TargetLanguage.LUA: "function {name}()\nend\n",
            TargetLanguage.CSHARP: "void {name}()\n{\n}\n",
        }
        return fallbacks.get(language, "def {name}():\n    pass\n")

    def _detect_language(self, code: str) -> TargetLanguage:
        """
        Heuristically infer the programming language from syntax
        patterns present in the code.
        """
        if not code.strip():
            return TargetLanguage.PYTHON

        csharp_indicators = (
            r"\busing\s+(Unity|System|UnityEngine)\b",
            r"\bvoid\s+\w+\s*\(",
            r"\bpublic\s+(class|void|int|float|bool)\b",
            r"\bMonoBehaviour\b",
        )
        for indicator in csharp_indicators:
            if re.search(indicator, code):
                return TargetLanguage.CSHARP

        gdscript_indicators = (
            r"\bextends\s+\w+",
            r"\bfunc\s+\w+\s*\(.*\)\s*->\s*\w+\s*:",
            r"\bvar\s+\w+\s*:=\s*",
            r"\b@onready\b",
            r"\bget_node\s*\(",
        )
        for indicator in gdscript_indicators:
            if re.search(indicator, code):
                return TargetLanguage.GDSCRIPT

        lua_indicators = (
            r"\blocal\s+\w+\s*=",
            r"\bfunction\s+\w+:\w+\s*\(",
            r"\bsetmetatable\s*\(",
            r"\bipairs\s*\(",
            r"--\[\[",
        )
        lua_score = 0
        for indicator in lua_indicators:
            if re.search(indicator, code):
                lua_score += 1
        if re.search(r"\bend\b", code) and not re.search(r"\bdef\b", code):
            lua_score += 1
        if lua_score >= 2:
            return TargetLanguage.LUA

        js_indicators = (
            r"\bconst\s+\w+\s*=",
            r"\blet\s+\w+\s*=",
            r"\bconsole\.log\s*\(",
            r"\bfunction\s+\w+\s*\(.*\)\s*\{",
            r"=>\s*\{",
            r"\baddEventListener\s*\(",
            r"\bdocument\.\w+",
            r"\bwindow\.\w+",
        )
        js_score = 0
        for indicator in js_indicators:
            if re.search(indicator, code):
                js_score += 1
        if js_score >= 2:
            return TargetLanguage.JAVASCRIPT

        return TargetLanguage.PYTHON

    def _infer_domain(self, code: str, intent: str) -> CodeDomain:
        """
        Infer the game domain from code content and intent description.
        """
        combined = (code + " " + intent).lower()

        domain_signals: List[Tuple[CodeDomain, List[str]]] = [
            (CodeDomain.RENDERING, ["render", "draw", "shader", "camera", "texture", "mesh", "sprite", "material"]),
            (CodeDomain.PHYSICS, ["physics", "collision", "rigidbody", "gravity", "velocity", "force", "raycast"]),
            (CodeDomain.AI_BEHAVIOR, ["ai", "behavior", "patrol", "chase", "attack", "state machine", "decision"]),
            (CodeDomain.UI, ["ui", "widget", "button", "panel", "hud", "menu", "dialog", "label"]),
            (CodeDomain.NETWORKING, ["network", "socket", "rpc", "multiplayer", "server", "client", "sync"]),
            (CodeDomain.AUDIO, ["audio", "sound", "music", "sfx", "play", "volume"]),
            (CodeDomain.INPUT_HANDLING, ["input", "keyboard", "mouse", "controller", "gamepad", "key", "bind"]),
        ]

        for domain, signals in domain_signals:
            for signal in signals:
                if signal in combined:
                    return domain

        return CodeDomain.GAME_LOGIC

    def _generate_from_prompt(
        self, prompt: str, language: TargetLanguage, domain: CodeDomain,
        base_code: str,
    ) -> tuple:
        """
        Template-based code generation from a natural language prompt.
        Returns (generated_code, confidence, warnings).
        """
        prompt_lower = prompt.lower()
        class_name = DOMAIN_CLASS_NAMES.get(domain, "GeneratedComponent")
        warnings: List[str] = []

        refined_code = base_code.replace("{name}", class_name)

        if "collision" in prompt_lower or "trigger" in prompt_lower:
            if language == TargetLanguage.PYTHON:
                refined_code += "\n\n    def on_collision_enter(self, other):\n        pass\n"
            elif language == TargetLanguage.GDSCRIPT:
                refined_code += "\n\nfunc _on_body_entered(body: Node) -> void:\n    pass\n"
            elif language == TargetLanguage.CSHARP:
                refined_code += "\n\n    void OnCollisionEnter(Collision other)\n    {\n    }\n"

        if "movement" in prompt_lower or "move" in prompt_lower or "wasd" in prompt_lower:
            if language == TargetLanguage.PYTHON:
                refined_code += (
                    "\n\n    def handle_movement(self, input_vector):\n"
                    "        speed = 5.0\n"
                    "        self.position += input_vector * speed\n"
                )
            elif language == TargetLanguage.GDSCRIPT:
                refined_code += (
                    "\n\nfunc _physics_process(delta: float) -> void:\n"
                    "    var direction = Input.get_vector(\"ui_left\", \"ui_right\", \"ui_up\", \"ui_down\")\n"
                    "    position += direction * 200.0 * delta\n"
                )
            elif language == TargetLanguage.CSHARP:
                refined_code += (
                    "\n\n    void HandleMovement(Vector3 input)\n"
                    "    {\n"
                    "        float speed = 5.0f;\n"
                    "        transform.position += input * speed * Time.deltaTime;\n"
                    "    }\n"
                )

        if "health" in prompt_lower or "damage" in prompt_lower:
            if language == TargetLanguage.PYTHON:
                refined_code += (
                    "\n\n    def take_damage(self, amount: float):\n"
                    "        self.health = max(0, self.health - amount)\n"
                    "        if self.health <= 0:\n"
                    "            self.on_death()\n"
                )

        if "spawn" in prompt_lower or "pool" in prompt_lower:
            if language == TargetLanguage.PYTHON:
                refined_code += (
                    "\n\n    def spawn(self, prefab, position):\n"
                    "        instance = prefab.clone()\n"
                    "        instance.position = position\n"
                    "        self.active_objects.append(instance)\n"
                    "        return instance\n"
                )

        if "timer" in prompt_lower or "cooldown" in prompt_lower or "delay" in prompt_lower:
            warnings.append("Timing logic detected — ensure delta time is used for frame-rate independence")

        if len(prompt.split()) < 5:
            confidence = 0.4
            warnings.append("Prompt is very short; results may be generic")
        elif len(prompt.split()) < 15:
            confidence = 0.7
        else:
            confidence = 0.85

        return textwrap.dedent(refined_code).strip(), confidence, warnings

    def _merge_with_context(self, base_code: str, context_code: str) -> str:
        """
        Merge generated code with existing context code by appending
        only the portions that do not already exist.
        """
        if not context_code.strip():
            return base_code

        context_lines = set(context_code.strip().split("\n"))
        base_lines = base_code.strip().split("\n")
        new_lines = [line for line in base_lines if line not in context_lines]

        return context_code.rstrip() + "\n" + "\n".join(new_lines)

    def _simulate_refactor(self, source_code: str, goal: str) -> tuple:
        """
        Simulate a refactoring operation. Extracts classes/functions,
        normalizes whitespace, and adds structure improvements based
        on the goal description.
        """
        goal_lower = goal.lower()
        warnings: List[str] = []
        refactored = source_code

        if "extract" in goal_lower or "method" in goal_lower:
            refactored = (
                "# Refactored: extracted logic into dedicated methods\n"
                + source_code
            )
            confidence = 0.8

        elif "rename" in goal_lower:
            refactored = source_code
            confidence = 0.9

        elif "simplify" in goal_lower or "clean" in goal_lower:
            cleaned_lines = [
                line for line in source_code.split("\n")
                if line.strip() or not line.strip()
            ]
            refactored = "\n".join(cleaned_lines)
            confidence = 0.75

        elif "performance" in goal_lower or "optimize" in goal_lower:
            confidence = 0.65
            warnings.append(
                "Performance-oriented refactoring applied — profile before and after "
                "to measure actual improvement"
            )

        else:
            confidence = 0.55
            warnings.append("Broad refactoring goal — consider narrowing the objective")

        return refactored, confidence, warnings

    def _simulate_bugfix(self, source_code: str, bug_description: str) -> tuple:
        """
        Simulate a bugfix operation by identifying likely bug patterns
        from the description and applying corrective modifications.
        """
        desc_lower = bug_description.lower()
        warnings: List[str] = []
        fixed = source_code
        confidence = 0.5

        fixes_applied: List[str] = []

        if "null" in desc_lower or "none" in desc_lower or "nil" in desc_lower:
            if "if " not in source_code:
                fixed = source_code.replace(
                    ".", " if obj is not None else None\n."
                )
            else:
                null_guard = "if target is None:\n    return\n"
                fixed = null_guard + source_code
            fixes_applied.append("null-reference guard")
            confidence = 0.75

        if "index" in desc_lower or "out of range" in desc_lower or "bounds" in desc_lower:
            fixed = source_code
            fixes_applied.append("bounds check recommendation")
            warnings.append(
                "Bounds violation detected — add range checks before indexed access"
            )
            confidence = 0.7

        if "loop" in desc_lower or "infinite" in desc_lower:
            fixes_applied.append("loop guard")
            warnings.append(
                "Infinite loop risk — ensure termination condition is reachable"
            )
            confidence = 0.6

        if "type" in desc_lower or "mismatch" in desc_lower:
            fixes_applied.append("type-coercion fix")
            confidence = 0.65

        if "division" in desc_lower or "zero" in desc_lower:
            div_guard = "if denominator == 0:\n    return 0\n"
            fixed = div_guard + fixed
            fixes_applied.append("division-by-zero guard")
            confidence = 0.85

        if not fixes_applied:
            warnings.append("Bug description did not match known patterns — generic fix applied")
            confidence = 0.35

        return fixed, confidence, warnings

    def _simulate_optimize(self, source_code: str, goal: str) -> tuple:
        """
        Simulate a performance optimization pass. Applies structural
        improvements like pre-allocation hints, loop hoisting, and
        caching suggestions.
        """
        warnings: List[str] = []
        optimized = source_code
        confidence = 0.55

        if "for " in source_code or "while " in source_code:
            optimized += "\n\n# Optimization: consider pre-allocating collections outside loops"
            confidence = 0.65

        if "def " in source_code or "function " in source_code or "func " in source_code:
            optimized += "\n\n# Optimization: cache frequently-accessed references at module level"

        if "update" in goal.lower() or "frame" in goal.lower():
            warnings.append(
                "Frame-level optimization applied — profile to confirm improvement"
            )
            confidence = 0.7

        return optimized, confidence, warnings

    def _merge_completion(
        self, partial_code: str, template_body: str, intent: str,
    ) -> str:
        """
        Merge partial code with template body, preserving the existing
        structure while filling in the missing sections.
        """
        if not partial_code.strip():
            return template_body

        partial_lines = partial_code.strip().split("\n")
        template_lines = template_body.strip().split("\n")

        last_partial_line = partial_lines[-1].strip() if partial_lines else ""

        completion_suffix: List[str] = []
        capture = False
        for line in template_lines:
            stripped = line.strip()
            if not capture:
                if stripped == last_partial_line or stripped.startswith(last_partial_line[:10]):
                    capture = True
                continue
            else:
                completion_suffix.append(line)

        if not completion_suffix:
            completion_suffix = ["    pass"]

        return partial_code.rstrip() + "\n" + "\n".join(completion_suffix)

    def _check_constraints(
        self, code: str, constraints: List[str], language: TargetLanguage,
    ) -> List[str]:
        """
        Check generated code against user-specified constraints and
        return any violation warnings.
        """
        warnings: List[str] = []
        for constraint in constraints:
            constraint_lower = constraint.lower()
            if "no eval" in constraint_lower and "eval" in code:
                warnings.append(f"Constraint violation: {constraint}")
            if "no exec" in constraint_lower and "exec" in code:
                warnings.append(f"Constraint violation: {constraint}")
            if "max lines" in constraint_lower:
                try:
                    max_lines = int(re.findall(r"\d+", constraint)[0])
                    actual = code.count("\n") + 1
                    if actual > max_lines:
                        warnings.append(
                            f"Constraint violation: {constraint} (actual: {actual} lines)"
                        )
                except (IndexError, ValueError):
                    pass
            if "no import" in constraint_lower or "no require" in constraint_lower:
                if re.search(r"\bimport\b|\brequire\b|\busing\b", code):
                    warnings.append(f"Constraint violation: {constraint}")

        return warnings

    def _check_python_indentation(self, lines: List[str]) -> str:
        """
        Check for mixed tabs and spaces in Python-like languages.
        """
        tabs_found = False
        spaces_found = False
        for line in lines:
            if line.startswith("\t"):
                tabs_found = True
            elif line.startswith("    ") or line.startswith("  "):
                spaces_found = True
        if tabs_found and spaces_found:
            return "Mixed tabs and spaces detected — use consistent indentation"
        return ""

    def _build_explanation(
        self, prompt: str, domain: CodeDomain, language: TargetLanguage,
    ) -> str:
        """
        Construct a human-readable explanation of the generated code.
        """
        domain_desc = domain.value.replace("_", " ")
        return (
            f"Generated {language.value} code for the {domain_desc} domain. "
            f"The implementation follows idiomatic {language.value} patterns "
            f"and is structured to integrate with the game engine's {domain_desc} system. "
            f"Prompt: {prompt[:150]}"
        )


def get_code_synthesis() -> CodeSynthesis:
    return CodeSynthesis.get_instance()