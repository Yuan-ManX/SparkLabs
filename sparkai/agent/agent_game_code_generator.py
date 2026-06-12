"""
SparkLabs Agent - Game Code Generator

AI-powered game code generator that translates natural language specifications
into executable game logic — including behaviors, scripts, mechanics, systems,
and shaders. Maintains a library of reusable code templates and generates
domain-specific code by matching templates and synthesizing procedural logic.

Architecture:
  AgentGameCodeGenerator (Singleton)
    |-- Template Library (reusable code blueprints across domains)
    |-- Code Synthesizer (template-matching + procedural generation)
    |-- Code Reviewer (quality scoring and issue detection)
    |-- Code Compiler (status progression through the code lifecycle)
    |-- Code Bundler (aggregate generated codes into deployable bundles)
    |-- Validator (static analysis of generated code)
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CodeLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    LUA = "lua"
    CSHARP = "csharp"


class CodeDomain(Enum):
    BEHAVIOR = "behavior"
    SCRIPT = "script"
    MECHANIC = "mechanic"
    SYSTEM = "system"
    SHADER = "shader"


class GenerationMode(Enum):
    TEMPLATE = "template"
    PROCEDURAL = "procedural"
    HYBRID = "hybrid"


class CodeStatus(Enum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    COMPILED = "compiled"
    TESTED = "tested"
    DEPLOYED = "deployed"


# ---------- Dataclasses ----------

@dataclass
class CodeTemplate:
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    language: CodeLanguage = CodeLanguage.PYTHON
    domain: CodeDomain = CodeDomain.BEHAVIOR
    template_code: str = ""
    parameters: List[str] = field(default_factory=list)
    description: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "language": self.language.value,
            "domain": self.domain.value,
            "template_code": self.template_code,
            "parameters": self.parameters,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class GenerationRequest:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    target_language: CodeLanguage = CodeLanguage.PYTHON
    target_domain: CodeDomain = CodeDomain.BEHAVIOR
    mode: GenerationMode = GenerationMode.HYBRID
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "description": self.description,
            "target_language": self.target_language.value,
            "target_domain": self.target_domain.value,
            "mode": self.mode.value,
            "context": self.context,
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class GeneratedCode:
    code_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    language: CodeLanguage = CodeLanguage.PYTHON
    domain: CodeDomain = CodeDomain.BEHAVIOR
    source_code: str = ""
    explanation: str = ""
    dependencies: List[str] = field(default_factory=list)
    template_references: List[str] = field(default_factory=list)
    status: CodeStatus = CodeStatus.DRAFT
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code_id": self.code_id,
            "request_id": self.request_id,
            "language": self.language.value,
            "domain": self.domain.value,
            "source_code": self.source_code,
            "explanation": self.explanation,
            "dependencies": self.dependencies,
            "template_references": self.template_references,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class CodeReview:
    review_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    code_id: str = ""
    reviewer_comments: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    issues_found: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    reviewed_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "code_id": self.code_id,
            "reviewer_comments": self.reviewer_comments,
            "quality_score": self.quality_score,
            "issues_found": self.issues_found,
            "suggestions": self.suggestions,
            "reviewed_at": self.reviewed_at,
        }


@dataclass
class CodeBundle:
    bundle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    codes: List[GeneratedCode] = field(default_factory=list)
    bundle_name: str = ""
    entry_point: str = ""
    compilation_order: List[str] = field(default_factory=list)
    total_lines: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "codes": [c.code_id for c in self.codes],
            "bundle_name": self.bundle_name,
            "entry_point": self.entry_point,
            "compilation_order": self.compilation_order,
            "total_lines": self.total_lines,
            "created_at": self.created_at,
        }


# ---------- Domain-specific code generators ----------

def _generate_behavior_code(name: str, language: CodeLanguage) -> str:
    """Generate an AI state machine behavior script."""
    if language == CodeLanguage.PYTHON:
        return (
            'import random\n'
            'from enum import Enum, auto\n\n'
            f'class {name}State(Enum):\n'
            '    IDLE = auto()\n'
            '    PATROL = auto()\n'
            '    CHASE = auto()\n'
            '    ATTACK = auto()\n'
            '    FLEE = auto()\n\n\n'
            f'class {name}Behavior:\n'
            f'    """AI-driven behavior controller for {name} entity."""\n\n'
            '    def __init__(self, entity):\n'
            '        self.entity = entity\n'
            '        self.state = {name}State.IDLE\n'
            '        self.state_elapsed = 0.0\n'
            '        self.aggro_range = 150.0\n'
            '        self.attack_range = 40.0\n'
            '        self.flee_health_threshold = 0.25\n\n'
            '    def update(self, delta_time: float, target):\n'
            '        self.state_elapsed += delta_time\n'
            '        distance = self.entity.distance_to(target)\n'
            '        health_ratio = self.entity.health / self.entity.max_health\n\n'
            '        if health_ratio < self.flee_health_threshold:\n'
            '            self._transition({name}State.FLEE)\n'
            '        elif distance <= self.attack_range:\n'
            '            self._transition({name}State.ATTACK)\n'
            '        elif distance <= self.aggro_range:\n'
            '            self._transition({name}State.CHASE)\n'
            '        elif self.state == {name}State.IDLE and self.state_elapsed > 3.0:\n'
            '            self._transition({name}State.PATROL)\n\n'
            '        self._execute_state(delta_time, target)\n\n'
            '    def _transition(self, new_state):\n'
            '        if self.state != new_state:\n'
            '            self.state = new_state\n'
            '            self.state_elapsed = 0.0\n\n'
            '    def _execute_state(self, dt, target):\n'
            '        actions = {{\n'
            '            {name}State.IDLE: self._do_idle,\n'
            '            {name}State.PATROL: self._do_patrol,\n'
            '            {name}State.CHASE: self._do_chase,\n'
            '            {name}State.ATTACK: self._do_attack,\n'
            '            {name}State.FLEE: self._do_flee,\n'
            '        }}\n'
            '        actions[self.state](dt, target)\n\n'
            '    def _do_idle(self, dt, target):\n'
            '        pass\n\n'
            '    def _do_patrol(self, dt, target):\n'
            '        if self.state_elapsed > 5.0:\n'
            '            self.entity.patrol_target = random.choice(self.entity.patrol_points)\n'
            '            self.state_elapsed = 0.0\n'
            '        self.entity.move_toward(self.entity.patrol_target, dt)\n\n'
            '    def _do_chase(self, dt, target):\n'
            '        self.entity.move_toward(target.position, dt * 1.5)\n\n'
            '    def _do_attack(self, dt, target):\n'
            '        if self.state_elapsed >= self.entity.attack_cooldown:\n'
            '            self.entity.perform_attack(target)\n'
            '            self.state_elapsed = 0.0\n\n'
            '    def _do_flee(self, dt, target):\n'
            '        flee_dir = self.entity.position - target.position\n'
            '        self.entity.move_toward(self.entity.position + flee_dir, dt * 1.2)\n'
        )
    elif language == CodeLanguage.JAVASCRIPT:
        return (
            'const State = {\n'
            '    IDLE: "idle",\n'
            '    PATROL: "patrol",\n'
            '    CHASE: "chase",\n'
            '    ATTACK: "attack",\n'
            '    FLEE: "flee",\n'
            '};\n\n'
            f'class {name}Behavior {{\n'
            f'    constructor(entity) {{\n'
            '        this.entity = entity;\n'
            '        this.state = State.IDLE;\n'
            '        this.stateElapsed = 0;\n'
            '        this.aggroRange = 150;\n'
            '        this.attackRange = 40;\n'
            '        this.fleeHealthThreshold = 0.25;\n'
            '    }}\n\n'
            '    update(deltaTime, target) {\n'
            '        this.stateElapsed += deltaTime;\n'
            '        const distance = this.entity.distanceTo(target);\n'
            '        const healthRatio = this.entity.health / this.entity.maxHealth;\n\n'
            '        if (healthRatio < this.fleeHealthThreshold) this._transition(State.FLEE);\n'
            '        else if (distance <= this.attackRange) this._transition(State.ATTACK);\n'
            '        else if (distance <= this.aggroRange) this._transition(State.CHASE);\n'
            '        else if (this.state === State.IDLE && this.stateElapsed > 3) this._transition(State.PATROL);\n\n'
            '        this._executeState(deltaTime, target);\n'
            '    }}\n\n'
            '    _transition(newState) {\n'
            '        if (this.state !== newState) { this.state = newState; this.stateElapsed = 0; }\n'
            '    }}\n\n'
            '    _executeState(dt, target) {\n'
            '        switch (this.state) {\n'
            '            case State.IDLE: break;\n'
            '            case State.PATROL: this._doPatrol(dt); break;\n'
            '            case State.CHASE: this._doChase(dt, target); break;\n'
            '            case State.ATTACK: this._doAttack(dt, target); break;\n'
            '            case State.FLEE: this._doFlee(dt, target); break;\n'
            '        }\n'
            '    }}\n\n'
            '    _doPatrol(dt) {\n'
            '        if (this.stateElapsed > 5) {\n'
            '            const idx = Math.floor(Math.random() * this.entity.patrolPoints.length);\n'
            '            this.entity.patrolTarget = this.entity.patrolPoints[idx];\n'
            '            this.stateElapsed = 0;\n'
            '        }\n'
            '        this.entity.moveToward(this.entity.patrolTarget, dt);\n'
            '    }}\n\n'
            '    _doChase(dt, target) { this.entity.moveToward(target.position, dt * 1.5); }\n'
            '    _doAttack(dt, target) {\n'
            '        if (this.stateElapsed >= this.entity.attackCooldown) {\n'
            '            this.entity.performAttack(target); this.stateElapsed = 0;\n'
            '        }\n'
            '    }}\n'
            '    _doFlee(dt, target) {\n'
            '        const dx = this.entity.x - target.x;\n'
            '        const dy = this.entity.y - target.y;\n'
            '        this.entity.moveToward({ x: this.entity.x + dx, y: this.entity.y + dy }, dt * 1.2);\n'
            '    }}\n'
            '}}\n'
        )
    else:
        return (
            f'-- AI Behavior: {name}\n'
            f'local {name}Behavior = {{}}\n'
            f'{name}Behavior.__index = {name}Behavior\n\n'
            f'function {name}Behavior:new(entity)\n'
            f'    local obj = {{\n'
            f'        entity = entity,\n'
            f'        state = "idle",\n'
            f'        stateElapsed = 0,\n'
            f'        aggroRange = 150,\n'
            f'        attackRange = 40,\n'
            f'        fleeThreshold = 0.25,\n'
            f'    }}\n'
            f'    setmetatable(obj, self)\n'
            f'    return obj\n'
            f'end\n\n'
            f'function {name}Behavior:update(dt, target)\n'
            f'    self.stateElapsed = self.stateElapsed + dt\n'
            f'    local dist = self.entity:distanceTo(target)\n'
            f'    local hp = self.entity.health / self.entity.maxHealth\n'
            f'    if hp < self.fleeThreshold then self:_transition("flee")\n'
            f'    elseif dist <= self.attackRange then self:_transition("attack")\n'
            f'    elseif dist <= self.aggroRange then self:_transition("chase")\n'
            f'    elseif self.state == "idle" and self.stateElapsed > 3 then self:_transition("patrol")\n'
            f'    end\n'
            f'    self:_execute(dt, target)\n'
            f'end\n\n'
            f'function {name}Behavior:_transition(s)\n'
            f'    if self.state ~= s then self.state = s; self.stateElapsed = 0 end\n'
            f'end\n\n'
            f'function {name}Behavior:_execute(dt, target)\n'
            f'    if self.state == "patrol" then self:_patrol(dt)\n'
            f'    elseif self.state == "chase" then self:_chase(dt, target)\n'
            f'    elseif self.state == "attack" then self:_attack(dt, target)\n'
            f'    elseif self.state == "flee" then self:_flee(dt, target)\n'
            f'    end\n'
            f'end\n\n'
            f'function {name}Behavior:_patrol(dt) self.entity:moveToward(self.entity.patrolTarget, dt) end\n'
            f'function {name}Behavior:_chase(dt, t) self.entity:moveToward(t.position, dt * 1.5) end\n'
            f'function {name}Behavior:_attack(dt, t)\n'
            f'    if self.stateElapsed >= self.entity.attackCooldown then self.entity:performAttack(t); self.stateElapsed = 0 end\n'
            f'end\n'
            f'function {name}Behavior:_flee(dt, t)\n'
            f'    local dx, dy = self.entity.x - t.x, self.entity.y - t.y\n'
            f'    self.entity:moveToward({{x = self.entity.x + dx, y = self.entity.y + dy}}, dt * 1.2)\n'
            f'end\n'
        )


def _generate_script_code(name: str, language: CodeLanguage) -> str:
    """Generate a game event handling script."""
    if language == CodeLanguage.PYTHON:
        return (
            f'class {name}Script:\n'
            f'    """Event-driven game script for {name}."""\n\n'
            '    def __init__(self, game_context):\n'
            '        self.ctx = game_context\n'
            '        self._listeners = {}\n'
            '        self._register_events()\n\n'
            '    def _register_events(self):\n'
            '        self.on("entity_spawned", self._on_entity_spawned)\n'
            '        self.on("item_collected", self._on_item_collected)\n'
            '        self.on("zone_entered", self._on_zone_entered)\n'
            '        self.on("dialogue_trigger", self._on_dialogue_trigger)\n\n'
            '    def on(self, event_name, handler):\n'
            '        self._listeners.setdefault(event_name, []).append(handler)\n\n'
            '    def emit(self, event_name, **kwargs):\n'
            '        for handler in self._listeners.get(event_name, []):\n'
            '            handler(kwargs)\n\n'
            '    def _on_entity_spawned(self, data):\n'
            '        entity = data.get("entity")\n'
            '        if entity and entity.type == "enemy":\n'
            '            self.ctx.log(f"Enemy spawned at {{entity.position}}")\n\n'
            '    def _on_item_collected(self, data):\n'
            '        item = data.get("item")\n'
            '        player = data.get("player")\n'
            '        if item and player:\n'
            '            player.inventory.add(item)\n'
            '            self.ctx.log(f"{{player.name}} collected {{item.name}}")\n\n'
            '    def _on_zone_entered(self, data):\n'
            '        zone = data.get("zone")\n'
            '        entity = data.get("entity")\n'
            '        if zone.trigger_type == "checkpoint":\n'
            '            self.ctx.set_checkpoint(zone.position)\n'
            '        elif zone.trigger_type == "cutscene":\n'
            '            self.ctx.play_cutscene(zone.cutscene_id)\n\n'
            '    def _on_dialogue_trigger(self, data):\n'
            '        npc = data.get("npc")\n'
            '        if npc and npc.dialogue_tree:\n'
            '            self.ctx.ui.show_dialogue(npc.dialogue_tree)\n'
        )
    elif language == CodeLanguage.JAVASCRIPT:
        return (
            f'export class {name}Script {{\n'
            f'    constructor(gameContext) {{\n'
            '        this.ctx = gameContext;\n'
            '        this._listeners = {};\n'
            '        this._registerEvents();\n'
            '    }}\n\n'
            '    _registerEvents() {\n'
            '        this.on("entitySpawned", this._onEntitySpawned.bind(this));\n'
            '        this.on("itemCollected", this._onItemCollected.bind(this));\n'
            '        this.on("zoneEntered", this._onZoneEntered.bind(this));\n'
            '        this.on("dialogueTrigger", this._onDialogueTrigger.bind(this));\n'
            '    }}\n\n'
            '    on(eventName, handler) {\n'
            '        if (!this._listeners[eventName]) this._listeners[eventName] = [];\n'
            '        this._listeners[eventName].push(handler);\n'
            '    }}\n\n'
            '    emit(eventName, data) {\n'
            '        const handlers = this._listeners[eventName] || [];\n'
            '        handlers.forEach(h => h(data));\n'
            '    }}\n\n'
            '    _onEntitySpawned(data) {\n'
            '        const entity = data.entity;\n'
            '        if (entity && entity.type === "enemy") {\n'
            '            this.ctx.log(`Enemy spawned at ${{entity.position}}`);\n'
            '        }\n'
            '    }}\n\n'
            '    _onItemCollected(data) {\n'
            '        const {{ item, player }} = data;\n'
            '        if (item && player) {\n'
            '            player.inventory.add(item);\n'
            '            this.ctx.log(`${{player.name}} collected ${{item.name}}`);\n'
            '        }\n'
            '    }}\n\n'
            '    _onZoneEntered(data) {\n'
            '        const {{ zone, entity }} = data;\n'
            '        if (zone.triggerType === "checkpoint") this.ctx.setCheckpoint(zone.position);\n'
            '        else if (zone.triggerType === "cutscene") this.ctx.playCutscene(zone.cutsceneId);\n'
            '    }}\n\n'
            '    _onDialogueTrigger(data) {\n'
            '        const npc = data.npc;\n'
            '        if (npc && npc.dialogueTree) this.ctx.ui.showDialogue(npc.dialogueTree);\n'
            '    }}\n'
            '}}\n'
        )
    else:
        return (
            f'-- Game Script: {name}\n'
            f'local {name}Script = {{}}\n'
            f'{name}Script.__index = {name}Script\n\n'
            f'function {name}Script:new(ctx)\n'
            f'    local obj = {{ctx = ctx, listeners = {{}}}}\n'
            f'    setmetatable(obj, self)\n'
            f'    obj:_register()\n'
            f'    return obj\n'
            f'end\n\n'
            f'function {name}Script:_register()\n'
            f'    self:on("entity_spawned", function(d) self:_onEntitySpawned(d) end)\n'
            f'    self:on("item_collected", function(d) self:_onItemCollected(d) end)\n'
            f'    self:on("zone_entered", function(d) self:_onZoneEntered(d) end)\n'
            f'end\n\n'
            f'function {name}Script:on(event, handler)\n'
            f'    self.listeners[event] = self.listeners[event] or {{}}\n'
            f'    table.insert(self.listeners[event], handler)\n'
            f'end\n\n'
            f'function {name}Script:emit(event, data)\n'
            f'    for _, h in ipairs(self.listeners[event] or {{}}) do h(data) end\n'
            f'end\n\n'
            f'function {name}Script:_onEntitySpawned(data)\n'
            f'    if data.entity and data.entity.type == "enemy" then\n'
            f'        self.ctx:log("Enemy spawned at " .. tostring(data.entity.position))\n'
            f'    end\n'
            f'end\n\n'
            f'function {name}Script:_onItemCollected(data)\n'
            f'    if data.item and data.player then\n'
            f'        data.player.inventory:add(data.item)\n'
            f'    end\n'
            f'end\n\n'
            f'function {name}Script:_onZoneEntered(data)\n'
            f'    local zone = data.zone\n'
            f'    if zone.triggerType == "checkpoint" then self.ctx:setCheckpoint(zone.position)\n'
            f'    elseif zone.triggerType == "cutscene" then self.ctx:playCutscene(zone.cutsceneId) end\n'
            f'end\n'
        )


def _generate_mechanic_code(name: str, language: CodeLanguage) -> str:
    """Generate a game mechanic system (score/movement/combat)."""
    if language == CodeLanguage.PYTHON:
        return (
            f'class {name}Mechanic:\n'
            f'    """Core game mechanic: {name}."""\n\n'
            '    def __init__(self, owner):\n'
            '        self.owner = owner\n'
            '        self.active = True\n'
            '        self.cooldown = 0.0\n'
            '        self.cooldown_duration = 2.0\n'
            '        self.power = 10.0\n'
            '        self.range = 100.0\n'
            '        self.combo_count = 0\n'
            '        self.combo_window = 1.5\n'
            '        self.combo_timer = 0.0\n\n'
            '    def update(self, delta_time: float):\n'
            '        if self.cooldown > 0:\n'
            '            self.cooldown = max(0.0, self.cooldown - delta_time)\n'
            '        if self.combo_timer > 0:\n'
            '            self.combo_timer -= delta_time\n'
            '            if self.combo_timer <= 0:\n'
            '                self.combo_count = 0\n\n'
            '    def execute(self, target) -> bool:\n'
            '        if not self.active or self.cooldown > 0:\n'
            '            return False\n'
            '        if self.owner.distance_to(target) > self.range:\n'
            '            return False\n'
            '        damage = self.power * (1.0 + self.combo_count * 0.15)\n'
            '        target.take_damage(damage)\n'
            '        self.cooldown = self.cooldown_duration\n'
            '        self.combo_count += 1\n'
            '        self.combo_timer = self.combo_window\n'
            '        return True\n\n'
            '    def upgrade(self, power_bonus: float = 0, range_bonus: float = 0,\n'
            '                cooldown_mult: float = 1.0) -> None:\n'
            '        self.power += power_bonus\n'
            '        self.range += range_bonus\n'
            '        self.cooldown_duration *= cooldown_mult\n\n'
            '    def reset(self):\n'
            '        self.cooldown = 0.0\n'
            '        self.combo_count = 0\n'
            '        self.combo_timer = 0.0\n'
        )
    elif language == CodeLanguage.JAVASCRIPT:
        return (
            f'export class {name}Mechanic {{\n'
            f'    constructor(owner) {{\n'
            '        this.owner = owner;\n'
            '        this.active = true;\n'
            '        this.cooldown = 0;\n'
            '        this.cooldownDuration = 2.0;\n'
            '        this.power = 10;\n'
            '        this.range = 100;\n'
            '        this.comboCount = 0;\n'
            '        this.comboWindow = 1.5;\n'
            '        this.comboTimer = 0;\n'
            '    }}\n\n'
            '    update(deltaTime) {\n'
            '        if (this.cooldown > 0) this.cooldown = Math.max(0, this.cooldown - deltaTime);\n'
            '        if (this.comboTimer > 0) {\n'
            '            this.comboTimer -= deltaTime;\n'
            '            if (this.comboTimer <= 0) this.comboCount = 0;\n'
            '        }\n'
            '    }}\n\n'
            '    execute(target) {\n'
            '        if (!this.active || this.cooldown > 0) return false;\n'
            '        if (this.owner.distanceTo(target) > this.range) return false;\n'
            '        const damage = this.power * (1 + this.comboCount * 0.15);\n'
            '        target.takeDamage(damage);\n'
            '        this.cooldown = this.cooldownDuration;\n'
            '        this.comboCount++;\n'
            '        this.comboTimer = this.comboWindow;\n'
            '        return true;\n'
            '    }}\n\n'
            '    upgrade(powerBonus = 0, rangeBonus = 0, cooldownMult = 1.0) {\n'
            '        this.power += powerBonus;\n'
            '        this.range += rangeBonus;\n'
            '        this.cooldownDuration *= cooldownMult;\n'
            '    }}\n\n'
            '    reset() {\n'
            '        this.cooldown = 0;\n'
            '        this.comboCount = 0;\n'
            '        this.comboTimer = 0;\n'
            '    }}\n'
            '}}\n'
        )
    else:
        return (
            f'-- Mechanic: {name}\n'
            f'local {name}Mechanic = {{}}\n'
            f'{name}Mechanic.__index = {name}Mechanic\n\n'
            f'function {name}Mechanic:new(owner)\n'
            f'    return setmetatable({{\n'
            f'        owner = owner, active = true, cooldown = 0,\n'
            f'        cooldownDuration = 2.0, power = 10, range = 100,\n'
            f'        comboCount = 0, comboWindow = 1.5, comboTimer = 0,\n'
            f'    }}, self)\n'
            f'end\n\n'
            f'function {name}Mechanic:update(dt)\n'
            f'    self.cooldown = math.max(0, self.cooldown - dt)\n'
            f'    self.comboTimer = self.comboTimer - dt\n'
            f'    if self.comboTimer <= 0 then self.comboCount = 0 end\n'
            f'end\n\n'
            f'function {name}Mechanic:execute(target)\n'
            f'    if not self.active or self.cooldown > 0 then return false end\n'
            f'    if self.owner:distanceTo(target) > self.range then return false end\n'
            f'    local dmg = self.power * (1 + self.comboCount * 0.15)\n'
            f'    target:takeDamage(dmg)\n'
            f'    self.cooldown = self.cooldownDuration\n'
            f'    self.comboCount = self.comboCount + 1\n'
            f'    self.comboTimer = self.comboWindow\n'
            f'    return true\n'
            f'end\n\n'
            f'function {name}Mechanic:upgrade(pBonus, rBonus, cdMult)\n'
            f'    self.power = self.power + (pBonus or 0)\n'
            f'    self.range = self.range + (rBonus or 0)\n'
            f'    self.cooldownDuration = self.cooldownDuration * (cdMult or 1.0)\n'
            f'end\n\n'
            f'function {name}Mechanic:reset()\n'
            f'    self.cooldown = 0; self.comboCount = 0; self.comboTimer = 0\n'
            f'end\n'
        )


def _generate_system_code(name: str, language: CodeLanguage) -> str:
    """Generate backend game system logic."""
    if language == CodeLanguage.PYTHON:
        return (
            f'class {name}System:\n'
            f'    """Game system manager for {name}."""\n\n'
            '    def __init__(self):\n'
            '        self.entities = {}\n'
            '        self._pending_additions = []\n'
            '        self._pending_removals = []\n'
            '        self._entity_counter = 0\n'
            '        self.is_initialized = False\n\n'
            '    def initialize(self, config: dict = None):\n'
            '        config = config or {}\n'
            '        self.entity_capacity = config.get("max_entities", 1024)\n'
            '        self.update_frequency = config.get("update_frequency", 60)\n'
            '        self.is_initialized = True\n\n'
            '    def register_entity(self, entity) -> str:\n'
            '        if len(self.entities) >= self.entity_capacity:\n'
            '            raise RuntimeError("Entity capacity exceeded")\n'
            '        self._entity_counter += 1\n'
            '        entity_id = f"eid_{{self._entity_counter:06d}}"\n'
            '        self._pending_additions.append((entity_id, entity))\n'
            '        return entity_id\n\n'
            '    def unregister_entity(self, entity_id: str):\n'
            '        if entity_id in self.entities or any(eid == entity_id for eid, _ in self._pending_additions):\n'
            '            self._pending_removals.append(entity_id)\n\n'
            '    def update(self, delta_time: float):\n'
            '        self._flush_pending()\n'
            '        for entity_id, entity in self.entities.items():\n'
            '            if hasattr(entity, "update"):\n'
            '                entity.update(delta_time)\n\n'
            '    def _flush_pending(self):\n'
            '        for entity_id, entity in self._pending_additions:\n'
            '            self.entities[entity_id] = entity\n'
            '        self._pending_additions.clear()\n'
            '        for entity_id in self._pending_removals:\n'
            '            self.entities.pop(entity_id, None)\n'
            '        self._pending_removals.clear()\n\n'
            '    def get_entity(self, entity_id: str):\n'
            '        return self.entities.get(entity_id)\n\n'
            '    def query(self, predicate) -> list:\n'
            '        return [e for e in self.entities.values() if predicate(e)]\n\n'
            '    def get_stats(self) -> dict:\n'
            '        return {\n'
            '            "total_entities": len(self.entities),\n'
            '            "capacity": self.entity_capacity,\n'
            '            "utilization_pct": round(len(self.entities) / max(self.entity_capacity, 1) * 100, 1),\n'
            '        }\n'
        )
    elif language == CodeLanguage.JAVASCRIPT:
        return (
            f'export class {name}System {{\n'
            f'    constructor() {{\n'
            '        this.entities = {};\n'
            '        this._pendingAdditions = [];\n'
            '        this._pendingRemovals = [];\n'
            '        this._entityCounter = 0;\n'
            '        this.isInitialized = false;\n'
            '        this.entityCapacity = 1024;\n'
            '        this.updateFrequency = 60;\n'
            '    }}\n\n'
            '    initialize(config = {{}}) {\n'
            '        this.entityCapacity = config.maxEntities || 1024;\n'
            '        this.updateFrequency = config.updateFrequency || 60;\n'
            '        this.isInitialized = true;\n'
            '    }}\n\n'
            '    registerEntity(entity) {\n'
            '        if (Object.keys(this.entities).length >= this.entityCapacity) {\n'
            '            throw new Error("Entity capacity exceeded");\n'
            '        }\n'
            '        this._entityCounter++;\n'
            '        const entityId = `eid_${{String(this._entityCounter).padStart(6, "0")}}`;\n'
            '        this._pendingAdditions.push([entityId, entity]);\n'
            '        return entityId;\n'
            '    }}\n\n'
            '    unregisterEntity(entityId) {\n'
            '        this._pendingRemovals.push(entityId);\n'
            '    }}\n\n'
            '    update(deltaTime) {\n'
            '        this._flushPending();\n'
            '        for (const [id, entity] of Object.entries(this.entities)) {\n'
            '            if (typeof entity.update === "function") entity.update(deltaTime);\n'
            '        }\n'
            '    }}\n\n'
            '    _flushPending() {\n'
            '        for (const [id, entity] of this._pendingAdditions) this.entities[id] = entity;\n'
            '        this._pendingAdditions.length = 0;\n'
            '        for (const id of this._pendingRemovals) delete this.entities[id];\n'
            '        this._pendingRemovals.length = 0;\n'
            '    }}\n\n'
            '    getEntity(entityId) {\n'
            '        return this.entities[entityId] || null;\n'
            '    }}\n\n'
            '    query(predicate) {\n'
            '        return Object.values(this.entities).filter(predicate);\n'
            '    }}\n\n'
            '    getStats() {\n'
            '        const total = Object.keys(this.entities).length;\n'
            '        return {\n'
            '            totalEntities: total,\n'
            '            capacity: this.entityCapacity,\n'
            '            utilizationPct: Math.round(total / Math.max(this.entityCapacity, 1) * 1000) / 10,\n'
            '        };\n'
            '    }}\n'
            '}}\n'
        )
    else:
        return (
            f'-- System: {name}\n'
            f'local {name}System = {{}}\n'
            f'{name}System.__index = {name}System\n\n'
            f'function {name}System:new()\n'
            f'    return setmetatable({{\n'
            f'        entities = {{}}, pendingAdd = {{}}, pendingRemove = {{}},\n'
            f'        counter = 0, initialized = false, capacity = 1024, freq = 60,\n'
            f'    }}, self)\n'
            f'end\n\n'
            f'function {name}System:initialize(cfg)\n'
            f'    cfg = cfg or {{}}\n'
            f'    self.capacity = cfg.maxEntities or 1024\n'
            f'    self.freq = cfg.updateFrequency or 60\n'
            f'    self.initialized = true\n'
            f'end\n\n'
            f'function {name}System:registerEntity(e)\n'
            f'    if #self.entities >= self.capacity then error("capacity exceeded") end\n'
            f'    self.counter = self.counter + 1\n'
            f'    local eid = string.format("eid_%06d", self.counter)\n'
            f'    table.insert(self.pendingAdd, {{eid, e}})\n'
            f'    return eid\n'
            f'end\n\n'
            f'function {name}System:unregisterEntity(eid)\n'
            f'    table.insert(self.pendingRemove, eid)\n'
            f'end\n\n'
            f'function {name}System:update(dt)\n'
            f'    self:_flush()\n'
            f'    for eid, e in pairs(self.entities) do\n'
            f'        if e.update then e:update(dt) end\n'
            f'    end\n'
            f'end\n\n'
            f'function {name}System:_flush()\n'
            f'    for _, pair in ipairs(self.pendingAdd) do self.entities[pair[1]] = pair[2] end\n'
            f'    self.pendingAdd = {{}}\n'
            f'    for _, eid in ipairs(self.pendingRemove) do self.entities[eid] = nil end\n'
            f'    self.pendingRemove = {{}}\n'
            f'end\n\n'
            f'function {name}System:getEntity(eid) return self.entities[eid] end\n\n'
            f'function {name}System:query(pred)\n'
            f'    local result = {{}}\n'
            f'    for _, e in pairs(self.entities) do if pred(e) then table.insert(result, e) end end\n'
            f'    return result\n'
            f'end\n\n'
            f'function {name}System:getStats()\n'
            f'    local n = 0; for _ in pairs(self.entities) do n = n + 1 end\n'
            f'    return {{total = n, capacity = self.capacity, pct = math.floor(n / self.capacity * 1000) / 10}}\n'
            f'end\n'
        )


def _generate_shader_code(name: str, language: CodeLanguage) -> str:
    """Generate a GLSL-like fragment shader."""
    return (
        f'// Shader: {name}\n'
        '#version 450\n\n'
        'layout(location = 0) in vec2 vTexCoord;\n'
        'layout(location = 0) out vec4 fragColor;\n\n'
        'uniform sampler2D uMainTexture;\n'
        'uniform float uTime;\n'
        'uniform vec2 uResolution;\n'
        'uniform vec3 uTintColor;\n'
        'uniform float uIntensity;\n\n'
        'void main() {\n'
        '    vec2 uv = vTexCoord;\n'
        '    vec2 centered = uv - 0.5;\n'
        '    float dist = length(centered);\n'
        '    float vignette = 1.0 - dist * uIntensity;\n'
        '    vec3 texColor = texture(uMainTexture, uv).rgb;\n'
        '    vec3 tinted = mix(texColor, uTintColor, 0.3);\n'
        '    vec3 finalColor = tinted * vignette;\n'
        '    float wave = sin(uv.y * 20.0 + uTime) * 0.05;\n'
        '    finalColor += wave * uTintColor;\n'
        '    fragColor = vec4(finalColor, 1.0);\n'
        '}\n'
    )


# ---------- Singleton ----------

class AgentGameCodeGenerator:
    """AI-powered game code generator that translates natural language specifications
    into executable game logic including behaviors, scripts, mechanics, and game rules."""

    _instance: Optional["AgentGameCodeGenerator"] = None
    _lock = threading.RLock()

    MAX_TEMPLATES = 200
    MAX_GENERATED = 1000

    def __init__(self):
        self._templates: Dict[str, CodeTemplate] = {}
        self._generated: Dict[str, GeneratedCode] = {}
        self._reviews: Dict[str, CodeReview] = {}
        self._bundles: Dict[str, CodeBundle] = {}
        self._generation_count: int = 0
        self._review_count: int = 0
        self._bundle_count: int = 0
        self._seed_templates()

    @classmethod
    def get_instance(cls) -> "AgentGameCodeGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---------- Template management ----------

    def _seed_templates(self) -> None:
        """Populate the template library with common built-in patterns."""
        seeds = [
            {
                "name": "State Machine Behavior",
                "language": CodeLanguage.PYTHON,
                "domain": CodeDomain.BEHAVIOR,
                "template_code": (
                    "class {EntityName}StateMachine:\n"
                    "    def __init__(self, entity):\n"
                    "        self.entity = entity\n"
                    "        self.current_state = 'idle'\n"
                    "        self.states = {{}}\n\n"
                    "    def add_state(self, name, on_enter=None, on_update=None, on_exit=None):\n"
                    "        self.states[name] = {{'enter': on_enter, 'update': on_update, 'exit': on_exit}}\n\n"
                    "    def transition(self, new_state):\n"
                    "        old = self.states.get(self.current_state)\n"
                    "        if old and old['exit']:\n"
                    "            old['exit'](self.entity)\n"
                    "        self.current_state = new_state\n"
                    "        new = self.states.get(new_state)\n"
                    "        if new and new['enter']:\n"
                    "            new['enter'](self.entity)\n\n"
                    "    def update(self, delta_time):\n"
                    "        state = self.states.get(self.current_state)\n"
                    "        if state and state['update']:\n"
                    "            state['update'](self.entity, delta_time)\n"
                ),
                "parameters": ["EntityName", "states", "transitions"],
                "description": "Generic finite state machine for entity AI behavior.",
            },
            {
                "name": "Event Dispatcher Script",
                "language": CodeLanguage.JAVASCRIPT,
                "domain": CodeDomain.SCRIPT,
                "template_code": (
                    "class EventDispatcher {\n"
                    "    constructor() {\n"
                    "        this._handlers = new Map();\n"
                    "    }\n"
                    "    on(event, handler, priority = 0) {\n"
                    "        if (!this._handlers.has(event)) this._handlers.set(event, []);\n"
                    "        this._handlers.get(event).push({ handler, priority });\n"
                    "        this._handlers.get(event).sort((a, b) => b.priority - a.priority);\n"
                    "    }\n"
                    "    off(event, handler) {\n"
                    "        const list = this._handlers.get(event);\n"
                    "        if (!list) return;\n"
                    "        this._handlers.set(event, list.filter(h => h.handler !== handler));\n"
                    "    }\n"
                    "    emit(event, data) {\n"
                    "        const list = this._handlers.get(event);\n"
                    "        if (!list) return;\n"
                    "        for (const { handler } of list) handler(data);\n"
                    "    }\n"
                    "    once(event, handler) {\n"
                    "        const wrapper = (data) => { this.off(event, wrapper); handler(data); };\n"
                    "        this.on(event, wrapper);\n"
                    "    }\n"
                    "}\n"
                ),
                "parameters": ["event_names", "handler_signatures"],
                "description": "Priority-based event dispatch system for game scripts.",
            },
            {
                "name": "Combat Mechanic Base",
                "language": CodeLanguage.PYTHON,
                "domain": CodeDomain.MECHANIC,
                "template_code": (
                    "class CombatMechanic:\n"
                    "    def __init__(self):\n"
                    "        self.attack_power = 10\n"
                    "        self.defense = 5\n"
                    "        self.critical_chance = 0.1\n"
                    "        self.critical_multiplier = 2.0\n"
                    "        self.elemental_type = 'physical'\n"
                    "        self.status_effects = []\n\n"
                    "    def calculate_damage(self, attacker_stats, defender_stats):\n"
                    "        base = max(1, attacker_stats['power'] - defender_stats['defense'] * 0.5)\n"
                    "        if random.random() < self.critical_chance:\n"
                    "            base *= self.critical_multiplier\n"
                    "        elemental_bonus = self._elemental_factor(defender_stats.get('element', 'physical'))\n"
                    "        return int(base * elemental_bonus)\n\n"
                    "    def _elemental_factor(self, defender_element):\n"
                    "        strengths = {{'fire': 'ice', 'ice': 'wind', 'wind': 'earth', 'earth': 'fire'}}\n"
                    "        return 1.5 if strengths.get(self.elemental_type) == defender_element else 1.0\n\n"
                    "    def apply_damage(self, target, damage):\n"
                    "        target.health -= damage\n"
                    "        if target.health <= 0:\n"
                    "            target.on_defeat()\n"
                    "        return damage\n"
                ),
                "parameters": ["attack_power", "defense", "elemental_type", "status_effects"],
                "description": "Base combat mechanic with elemental strengths and critical hits.",
            },
        ]

        for data in seeds:
            template = CodeTemplate(**data)
            self._templates[template.template_id] = template

    def create_template(
        self,
        name: str,
        language: str,
        domain: str,
        template_code: str,
        parameters: Optional[List[str]] = None,
        description: str = "",
    ) -> CodeTemplate:
        try:
            lang = CodeLanguage(language)
        except ValueError:
            lang = CodeLanguage.PYTHON
        try:
            dom = CodeDomain(domain)
        except ValueError:
            dom = CodeDomain.BEHAVIOR

        template = CodeTemplate(
            name=name,
            language=lang,
            domain=dom,
            template_code=template_code,
            parameters=parameters or [],
            description=description,
        )
        self._templates[template.template_id] = template

        if len(self._templates) > self.MAX_TEMPLATES:
            oldest = min(self._templates.values(), key=lambda t: t.created_at)
            del self._templates[oldest.template_id]

        return template

    def list_templates(
        self,
        domain: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[CodeTemplate]:
        results = list(self._templates.values())
        if domain is not None:
            try:
                dom = CodeDomain(domain)
                results = [t for t in results if t.domain == dom]
            except ValueError:
                pass
        if language is not None:
            try:
                lang = CodeLanguage(language)
                results = [t for t in results if t.language == lang]
            except ValueError:
                pass
        return results

    # ---------- Code generation ----------

    def generate_from_spec(
        self,
        description: str,
        target_language: str = "python",
        target_domain: str = "behavior",
        context: Optional[Dict[str, Any]] = None,
        mode: str = "hybrid",
    ) -> GeneratedCode:
        try:
            lang = CodeLanguage(target_language)
        except ValueError:
            lang = CodeLanguage.PYTHON
        try:
            dom = CodeDomain(target_domain)
        except ValueError:
            dom = CodeDomain.BEHAVIOR
        try:
            gen_mode = GenerationMode(mode)
        except ValueError:
            gen_mode = GenerationMode.HYBRID

        desc_lower = description.lower()
        entity_name = context.get("entity_name", "Entity") if context else "Entity"

        # Extract a name from the description
        words = description.replace("_", " ").replace("-", " ").split()
        name_words = [w.capitalize() for w in words[:2] if len(w) > 2]
        derived_name = "".join(name_words) if name_words else "Entity"

        # Match against templates for hybrid/template mode
        matched_template_ids: List[str] = []
        if gen_mode in (GenerationMode.TEMPLATE, GenerationMode.HYBRID):
            domain_templates = [t for t in self._templates.values() if t.domain == dom]
            for tpl in domain_templates:
                tpl_keywords = tpl.name.lower().split()
                if any(kw in desc_lower for kw in tpl_keywords):
                    matched_template_ids.append(tpl.template_id)

        # Generate domain-specific source code
        if dom == CodeDomain.BEHAVIOR:
            source_code = _generate_behavior_code(derived_name, lang)
            explanation = (
                f"Generated AI behavior '{derived_name}' with a 5-state finite state machine "
                f"(Idle, Patrol, Chase, Attack, Flee). Includes aggro range checks, "
                f"health-based flee logic, and cooldown-managed combat actions."
            )
            deps = ["random"] if lang == CodeLanguage.PYTHON else []
        elif dom == CodeDomain.SCRIPT:
            source_code = _generate_script_code(derived_name, lang)
            explanation = (
                f"Generated event-driven game script '{derived_name}' with registration for "
                f"entity_spawned, item_collected, zone_entered, and dialogue_trigger events. "
                f"Supports dynamic listener management and event emission."
            )
            deps = []
        elif dom == CodeDomain.MECHANIC:
            source_code = _generate_mechanic_code(derived_name, lang)
            explanation = (
                f"Generated game mechanic '{derived_name}' with cooldown management, "
                f"combo chaining (with decay timer), range checking, and an upgrade system. "
                f"Provides execute, update, upgrade, and reset methods."
            )
            deps = []
        elif dom == CodeDomain.SHADER:
            source_code = _generate_shader_code(derived_name, lang)
            explanation = (
                f"Generated shader '{derived_name}' with vignette effect, color tinting, "
                f"and animated wave distortion driven by uTime uniform."
            )
            deps = []
        else:
            source_code = _generate_system_code(derived_name, lang)
            explanation = (
                f"Generated backend system '{derived_name}' with entity registration, "
                f"pending addition/removal queues, predicate-based querying, and "
                f"capacity-limited storage."
            )
            deps = []

        code = GeneratedCode(
            request_id=uuid.uuid4().hex,
            language=lang,
            domain=dom,
            source_code=source_code,
            explanation=explanation,
            dependencies=deps,
            template_references=matched_template_ids,
            status=CodeStatus.DRAFT,
            metadata={
                "description": description,
                "mode": gen_mode.value,
                "entity_name": derived_name,
                "line_count": source_code.count("\n"),
                "template_match_count": len(matched_template_ids),
            },
        )
        self._generated[code.code_id] = code
        self._generation_count += 1

        if len(self._generated) > self.MAX_GENERATED:
            oldest = min(self._generated.values(), key=lambda c: c.created_at)
            del self._generated[oldest.code_id]

        return code

    def generate_from_template(
        self,
        template_id: str,
        parameters: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[GeneratedCode]:
        template = self._templates.get(template_id)
        if template is None:
            return None

        params = parameters or {}
        code_text = template.template_code
        for key, value in params.items():
            code_text = code_text.replace("{" + key + "}", str(value))

        code = GeneratedCode(
            request_id=uuid.uuid4().hex,
            language=template.language,
            domain=template.domain,
            source_code=code_text,
            explanation=f"Generated from template '{template.name}' with customized parameters.",
            dependencies=[],
            template_references=[template_id],
            status=CodeStatus.DRAFT,
            metadata={
                "template_name": template.name,
                "parameters": params,
                "context": context or {},
                "line_count": code_text.count("\n"),
            },
        )
        self._generated[code.code_id] = code
        self._generation_count += 1

        if len(self._generated) > self.MAX_GENERATED:
            oldest = min(self._generated.values(), key=lambda c: c.created_at)
            del self._generated[oldest.code_id]

        return code

    # ---------- Convenience generators ----------

    def generate_behavior(
        self,
        name: str,
        description: str,
        target_language: str = "python",
    ) -> GeneratedCode:
        return self.generate_from_spec(
            description=description,
            target_language=target_language,
            target_domain="behavior",
            context={"entity_name": name},
        )

    def generate_script(
        self,
        name: str,
        description: str,
        target_language: str = "python",
    ) -> GeneratedCode:
        return self.generate_from_spec(
            description=description,
            target_language=target_language,
            target_domain="script",
            context={"entity_name": name},
        )

    def generate_mechanic(
        self,
        name: str,
        description: str,
        target_language: str = "python",
    ) -> GeneratedCode:
        return self.generate_from_spec(
            description=description,
            target_language=target_language,
            target_domain="mechanic",
            context={"entity_name": name},
        )

    def create_shader(self, name: str, description: str) -> GeneratedCode:
        return self.generate_from_spec(
            description=description,
            target_language="python",
            target_domain="shader",
            context={"entity_name": name},
        )

    # ---------- Review ----------

    def review_code(self, code_id: str, criteria: Optional[List[str]] = None) -> Optional[CodeReview]:
        code = self._generated.get(code_id)
        if code is None:
            return None

        criteria = criteria or ["readability", "performance", "correctness", "maintainability"]
        comments: List[str] = []
        issues: List[str] = []
        suggestions: List[str] = []
        score = 100.0

        source = code.source_code

        # Readability checks
        if "readability" in criteria:
            avg_line_len = sum(len(line) for line in source.split("\n")) / max(source.count("\n"), 1)
            if avg_line_len > 80:
                issues.append("Some lines exceed 80 characters; consider wrapping.")
                score -= 5.0
            comments.append("Readability assessment completed based on line-length metrics.")

        # Performance checks
        if "performance" in criteria:
            loops = source.count("for ") + source.count("for(") + source.count("while ")
            if loops > 10:
                issues.append(f"High loop count ({loops}); review for potential overhead.")
                score -= 3.0
            comments.append(f"Performance scan detected {loops} loops.")

        # Correctness checks
        if "correctness" in criteria:
            has_return = "return" in source
            has_init = "def __init__" in source or "constructor" in source
            if not has_return and code.domain == CodeDomain.MECHANIC:
                issues.append("Mechanic code has no return statements; verify output interfaces.")
                score -= 4.0
            if not has_init:
                issues.append("No constructor/initializer found; entity setup may be incomplete.")
                score -= 3.0
            comments.append("Correctness scan performed; checked for init and return patterns.")

        # Maintainability checks
        if "maintainability" in criteria:
            if len(source) < 200:
                suggestions.append("Code is relatively short; consider adding docstrings for larger modules.")
            if source.count("#") < 3 and source.count("//") < 3:
                suggestions.append("Minimal inline comments detected; add context for complex logic.")
                score -= 2.0
            comments.append("Maintainability assessed from comment density.")

        score = max(0.0, min(100.0, score))
        if not issues:
            suggestions.append("No critical issues detected. Code is ready for integration.")

        # Update code status
        code.status = CodeStatus.REVIEWING

        review = CodeReview(
            code_id=code_id,
            reviewer_comments=comments,
            quality_score=round(score, 1),
            issues_found=issues,
            suggestions=suggestions,
        )
        self._reviews[review.review_id] = review
        self._review_count += 1

        return review

    # ---------- Compile ----------

    def compile_code(self, code_id: str) -> Optional[GeneratedCode]:
        code = self._generated.get(code_id)
        if code is None:
            return None
        code.status = CodeStatus.COMPILED
        return code

    # ---------- Bundle ----------

    def bundle_codes(
        self,
        code_ids: List[str],
        bundle_name: str,
        entry_point: str = "",
    ) -> Optional[CodeBundle]:
        codes: List[GeneratedCode] = []
        for cid in code_ids:
            code = self._generated.get(cid)
            if code is None:
                return None
            codes.append(code)

        total_lines = sum(c.source_code.count("\n") for c in codes)
        compilation_order = [c.code_id for c in codes]

        bundle = CodeBundle(
            codes=codes,
            bundle_name=bundle_name,
            entry_point=entry_point,
            compilation_order=compilation_order,
            total_lines=total_lines,
        )
        self._bundles[bundle.bundle_id] = bundle
        self._bundle_count += 1

        return bundle

    # ---------- Query ----------

    def list_generated(
        self,
        domain: Optional[str] = None,
        language: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[GeneratedCode]:
        results = list(self._generated.values())
        if domain is not None:
            try:
                dom = CodeDomain(domain)
                results = [c for c in results if c.domain == dom]
            except ValueError:
                pass
        if language is not None:
            try:
                lang = CodeLanguage(language)
                results = [c for c in results if c.language == lang]
            except ValueError:
                pass
        if status is not None:
            try:
                st = CodeStatus(status)
                results = [c for c in results if c.status == st]
            except ValueError:
                pass
        return results

    def get_code(self, code_id: str) -> Optional[GeneratedCode]:
        return self._generated.get(code_id)

    def delete_code(self, code_id: str) -> bool:
        if code_id in self._generated:
            del self._generated[code_id]
            return True
        return False

    # ---------- Validate ----------

    def validate_code(self, code_id: str) -> Dict[str, Any]:
        code = self._generated.get(code_id)
        if code is None:
            return {"error": f"Code '{code_id}' not found"}

        issues: List[Dict[str, str]] = []
        source = code.source_code

        # Language-specific syntax checks
        if code.language == CodeLanguage.PYTHON:
            if "def " not in source:
                issues.append({"severity": "warning", "message": "No function definitions found."})
            if "class " not in source and code.domain not in (CodeDomain.SHADER,):
                issues.append({"severity": "warning", "message": "No class definitions found."})
            if source.count("(") != source.count(")"):
                issues.append({"severity": "error", "message": "Mismatched parentheses."})
        elif code.language == CodeLanguage.JAVASCRIPT:
            if source.count("{") != source.count("}"):
                issues.append({"severity": "error", "message": "Mismatched curly braces."})
            if "class " not in source and "function " not in source and code.domain != CodeDomain.SHADER:
                issues.append({"severity": "warning", "message": "No class or function definitions found."})
        elif code.language == CodeLanguage.LUA:
            if source.count("function ") < 1 and code.domain != CodeDomain.SHADER:
                issues.append({"severity": "warning", "message": "No function definitions found."})

        # General code quality checks
        lines = source.split("\n")
        blank_ratio = sum(1 for l in lines if l.strip() == "") / max(len(lines), 1)
        if blank_ratio > 0.5:
            issues.append({"severity": "info", "message": "High blank-line ratio; consider compacting."})

        valid = len([i for i in issues if i["severity"] == "error"]) == 0

        return {
            "code_id": code_id,
            "valid": valid,
            "issue_count": len(issues),
            "error_count": len([i for i in issues if i["severity"] == "error"]),
            "warning_count": len([i for i in issues if i["severity"] == "warning"]),
            "issues": issues,
            "language": code.language.value,
            "domain": code.domain.value,
            "line_count": len(lines),
        }

    # ---------- Stats ----------

    def get_stats(self) -> Dict[str, Any]:
        by_language: Dict[str, int] = {}
        by_domain: Dict[str, int] = {}
        by_status: Dict[str, int] = {}

        for code in self._generated.values():
            by_language[code.language.value] = by_language.get(code.language.value, 0) + 1
            by_domain[code.domain.value] = by_domain.get(code.domain.value, 0) + 1
            by_status[code.status.value] = by_status.get(code.status.value, 0) + 1

        total_lines = sum(c.source_code.count("\n") for c in self._generated.values())

        return {
            "total_templates": len(self._templates),
            "total_generated": len(self._generated),
            "total_reviews": self._review_count,
            "total_bundles": self._bundle_count,
            "generation_count": self._generation_count,
            "by_language": by_language,
            "by_domain": by_domain,
            "by_status": by_status,
            "total_lines_generated": total_lines,
            "avg_lines_per_code": round(total_lines / max(len(self._generated), 1), 1),
        }


def get_game_code_generator() -> AgentGameCodeGenerator:
    return AgentGameCodeGenerator.get_instance()