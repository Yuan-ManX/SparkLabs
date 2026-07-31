"""
SparkLabs Agent - Lexical Identity Forge

The AgentLexicalIdentityForge models how agents forge a unique linguistic
identity through the words they choose, the phrases they repeat, and the
verbal tics that crystallize into a recognizable voice. An agent's voice is
not a preset - it is forged. Each utterance leaves a lexical deposit; over
time those deposits harden into verbal habits, habits curve into dialect,
and dialect hardens into identity.

Two agents can witness the same event and speak of it in utterly different
tongues. One soldier calls the field "hallowed"; another calls it "a
slaughterhouse waiting to happen." The difference is not random - it is the
accumulated weight of every word that agent has spoken before. The forge
treats language as a living material: agents utter, their utterances vary
with mood and context, variants crystallize into stable lexical preferences,
those preferences drift as the agent encounters new speech communities, and
the agent reconciles its forged voice with the social dialect around it.

Architecture:
  UTTER       ->  VARY       ->  CRYSTALLIZE ->  DRIFT     ->  RECONCILE
  (agents     (utterances    (recurring       (crystallized  (the forged
   produce    vary with      variants         voice drifts   voice is
   lexical    mood and       harden into      as the agent   reconciled
   utterances context)       stable           encounters     with the
   into the   )              lexical          new dialects)  surrounding
   forge)                    preferences)                    social voice)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class LexicalPhase(Enum):
    """Phases of the lexical identity forging cycle."""
    UTTER = "utter"              # agents produce lexical utterances
    VARY = "vary"                # utterances vary with mood and context
    CRYSTALLIZE = "crystallize"  # recurring variants harden into preferences
    DRIFT = "drift"              # crystallized voice drifts with new dialects
    RECONCILE = "reconcile"      # forged voice reconciles with social voice


class LexicalRegister(Enum):
    """Registers an agent can speak in."""
    FORMAL = "formal"            # ceremonial, official
    CASUAL = "casual"            # everyday speech
    INTIMATE = "intimate"        # close-company speech
    MARTIAL = "martial"          # military, commanding
    POETIC = "poetic"            # lyrical, metaphorical
    VULGAR = "vulgar"            # coarse, blunt
    ARCANE = "arcane"            # archaic, esoteric
    COLLOQUIAL = "colloquial"    # regional, slang


class WordClass(Enum):
    """Classes of lexical tokens that compose an agent's voice."""
    NOUN = "noun"                # naming words
    VERB = "verb"                # action words
    ADJECTIVE = "adjective"      # qualifying words
    ADVERB = "adverb"            # modifying words
    INTERJECTION = "interjection"  # verbal tics, exclamations
    METAPHOR = "metaphor"        # figurative anchors
    OATH = "oath"                # sworn phrases, invocations


class VoiceState(Enum):
    """State of an agent's forged voice."""
    RAW = "raw"                  # no crystallized identity yet
    FORMING = "forming"          # preferences beginning to harden
    DISTINCT = "distinct"        # recognizable voice established
    DRIFTING = "drifting"        # voice shifting under dialect pressure
    RECONCILING = "reconciling"  # voice merging with or resisting social voice
    FORGED = "forged"            # stable, matured lexical identity


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LexicalToken:
    """A single lexical token an agent has used."""
    token_id: str
    word: str
    word_class: WordClass
    register: LexicalRegister
    emotional_valence: float = 0.0       # -1.0 (dark) to 1.0 (bright)
    usage_count: int = 0
    first_used_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


@dataclass
class LexicalVariant:
    """A variant utterance produced by varying a base expression."""
    variant_id: str
    base_expression: str
    variant_text: str
    register: LexicalRegister
    mood_signature: float = 0.0          # mood that produced this variant
    strength: float = 0.1                # 0.0-1.0, how established
    occurrences: int = 0


@dataclass
class LexicalPreference:
    """A crystallized lexical preference in the agent's voice."""
    preference_id: str
    word_class: WordClass
    preferred_tokens: List[str] = field(default_factory=list)
    register_affinity: Dict[str, float] = field(default_factory=dict)
    strength: float = 0.0                # 0.0-1.0
    signature_phrase: str = ""           # a phrase that captures the voice


@dataclass
class DialectPressure:
    """Pressure from a surrounding dialect on the agent's voice."""
    pressure_id: str
    source: str                          # community or agent exerting pressure
    register: LexicalRegister
    intensity: float = 0.3               # 0.0-1.0
    tokens_introduced: List[str] = field(default_factory=list)
    applied_at: float = field(default_factory=time.time)


@dataclass
class LexicalAgent:
    """Per-agent forged voice state."""
    agent_id: str
    voice_state: VoiceState = VoiceState.RAW
    tokens: Dict[str, LexicalToken] = field(default_factory=dict)
    variants: Dict[str, LexicalVariant] = field(default_factory=dict)
    preferences: Dict[str, LexicalPreference] = field(default_factory=dict)
    dialect_pressures: Deque[DialectPressure] = field(default_factory=deque)
    voice_signature: str = ""            # distilled signature phrase
    voice_strength: float = 0.0          # 0.0-1.0, how forged
    dialect_drift: float = 0.0           # 0.0-1.0, how far from original
    reconciliation_tension: float = 0.0  # 0.0-1.0, social vs forged tension
    total_utterances: int = 0
    total_variants: int = 0
    total_crystallizations: int = 0


# =============================================================================
# Forge
# =============================================================================

class AgentLexicalIdentityForge:
    """
    Thread-safe singleton orchestrating lexical identity forging for agents.

    Usage:
        forge = AgentLexicalIdentityForge.get_instance()
        forge.register_agent("bard", default_register="poetic")
        forge.utter("bard", "u1", "the moon limps home", WordClass.METAPHOR,
                    LexicalRegister.POETIC, emotional_valence=0.4)
        forge.utter("bard", "u2", "the moon drags its wounded light",
                    WordClass.METAPHOR, LexicalRegister.POETIC, 0.3)
        forge.cycle()
        signature = forge.get_voice_signature("bard")
    """

    _instance: Optional["AgentLexicalIdentityForge"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _VARY_THRESHOLD = 2                  # usages before a token begins to vary
    _CRYSTALLIZE_THRESHOLD = 3           # occurrences before a variant hardens
    _CRYSTALLIZE_STRENGTH_GAIN = 0.15    # strength gained per crystallization
    _DRIFT_RATE = 0.08                   # how fast dialect pressure moves voice
    _RECONCILE_TENSION_DECAY = 0.10      # how fast reconciliation tension eases
    _RECONCILE_RESISTANCE = 0.4          # how strongly forged voice resists drift
    _SIGNATURE_STRENGTH_THRESHOLD = 0.5  # strength needed to mint a signature
    _MAX_TOKENS_PER_AGENT = 300
    _MAX_VARIANTS_PER_AGENT = 200
    _MAX_PREFERENCES_PER_AGENT = 80
    _MAX_DIALECT_PRESSURES = 30
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._agents: Dict[str, LexicalAgent] = {}
        self._phase: LexicalPhase = LexicalPhase.UTTER
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentLexicalIdentityForge":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "total_agents": 0,
            "total_utterances": 0,
            "total_variants": 0,
            "total_crystallizations": 0,
            "total_drifts": 0,
            "total_reconciliations": 0,
            "forged_voices": 0,
            "avg_voice_strength": 0.0,
            "avg_dialect_drift": 0.0,
            "avg_reconciliation_tension": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._agents:
            return
        strengths = [a.voice_strength for a in self._agents.values()]
        drifts = [a.dialect_drift for a in self._agents.values()]
        tensions = [a.reconciliation_tension for a in self._agents.values()]
        n = len(self._agents)
        self._stats["total_agents"] = n
        self._stats["forged_voices"] = sum(
            1 for a in self._agents.values() if a.voice_state == VoiceState.FORGED
        )
        self._stats["avg_voice_strength"] = sum(strengths) / n
        self._stats["avg_dialect_drift"] = sum(drifts) / n
        self._stats["avg_reconciliation_tension"] = sum(tensions) / n

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str, default_register: str = "casual") -> Dict[str, Any]:
        """Register a new agent for lexical identity forging."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            try:
                reg = LexicalRegister(default_register)
            except ValueError:
                return {"error": f"Invalid register: {default_register}"}
            agent = LexicalAgent(agent_id=agent_id)
            agent.preferences["__default_register__"] = LexicalPreference(
                preference_id="__default_register__",
                word_class=WordClass.INTERJECTION,
                register_affinity={reg.value: 0.5},
                strength=0.2,
            )
            self._agents[agent_id] = agent
            self._record_event("agent_registered", {
                "agent_id": agent_id,
                "default_register": reg.value,
            })
            return {
                "agent_id": agent_id,
                "voice_state": agent.voice_state.value,
                "default_register": reg.value,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and all forged voice material."""
        with self._global_lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._record_event("agent_removed", {
                "agent_id": agent_id,
                "tokens": len(agent.tokens),
                "preferences": len(agent.preferences),
            })
            return {
                "removed": agent_id,
                "cleared_tokens": len(agent.tokens),
                "cleared_variants": len(agent.variants),
                "cleared_preferences": len(agent.preferences),
            }

    # -------------------------------------------------------------------------
    # Utterance Intake
    # -------------------------------------------------------------------------

    def utter(self, agent_id: str, token_id: str, word: str,
              word_class: WordClass, register: LexicalRegister,
              emotional_valence: float = 0.0) -> Dict[str, Any]:
        """Record a lexical utterance from an agent."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            if token_id in agent.tokens:
                token = agent.tokens[token_id]
                token.usage_count += 1
                token.last_used_at = time.time()
            else:
                token = LexicalToken(
                    token_id=token_id,
                    word=word,
                    word_class=word_class,
                    register=register,
                    emotional_valence=max(-1.0, min(1.0, emotional_valence)),
                    usage_count=1,
                )
                agent.tokens[token_id] = token
                if len(agent.tokens) > self._MAX_TOKENS_PER_AGENT:
                    oldest = min(agent.tokens, key=lambda tid: agent.tokens[tid].first_used_at)
                    agent.tokens.pop(oldest, None)
            agent.total_utterances += 1
            self._stats["total_utterances"] += 1
            self._record_event("utterance", {
                "agent_id": agent_id,
                "token_id": token_id,
                "word": word,
                "word_class": word_class.value,
                "register": register.value,
            })
            return {
                "agent_id": agent_id,
                "token_id": token_id,
                "word": word,
                "usage_count": token.usage_count,
                "total_utterances": agent.total_utterances,
            }

    def apply_dialect_pressure(self, agent_id: str, source: str,
                               register: LexicalRegister, intensity: float = 0.3,
                               tokens_introduced: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply dialect pressure from a surrounding community."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            pressure = DialectPressure(
                pressure_id=f"dp_{int(time.time()*1000)}_{random.randint(0,999)}",
                source=source,
                register=register,
                intensity=max(0.0, min(1.0, intensity)),
                tokens_introduced=tokens_introduced or [],
            )
            agent.dialect_pressures.append(pressure)
            if len(agent.dialect_pressures) > self._MAX_DIALECT_PRESSURES:
                agent.dialect_pressures.popleft()
            self._record_event("dialect_pressure", {
                "agent_id": agent_id,
                "source": source,
                "register": register.value,
                "intensity": pressure.intensity,
            })
            return {
                "agent_id": agent_id,
                "source": source,
                "register": register.value,
                "intensity": pressure.intensity,
                "tokens_introduced": pressure.tokens_introduced,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single lexical identity forging cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = LexicalPhase.UTTER
            phase_outputs["utter"] = self._phase_utter()
            self._phase = LexicalPhase.VARY
            phase_outputs["vary"] = self._phase_vary()
            self._phase = LexicalPhase.CRYSTALLIZE
            phase_outputs["crystallize"] = self._phase_crystallize()
            self._phase = LexicalPhase.DRIFT
            phase_outputs["drift"] = self._phase_drift()
            self._phase = LexicalPhase.RECONCILE
            phase_outputs["reconcile"] = self._phase_reconcile()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_utter(self) -> Dict[str, Any]:
        """Utter phase: tally the lexical substrate of each agent."""
        total_tokens = 0
        for agent in self._agents.values():
            total_tokens += len(agent.tokens)
            if agent.voice_state == VoiceState.RAW and agent.total_utterances >= 3:
                agent.voice_state = VoiceState.FORMING
        self._record_event("phase_utter", {"total_tokens": total_tokens})
        return {
            "agents": len(self._agents),
            "total_tokens": total_tokens,
        }

    def _phase_vary(self) -> Dict[str, Any]:
        """Vary phase: tokens used enough times spawn variant utterances."""
        variants_created = 0
        for agent in self._agents.values():
            for token in list(agent.tokens.values()):
                if token.usage_count < self._VARY_THRESHOLD:
                    continue
                # Generate a variant by modulating the word with mood.
                mood_sig = random.uniform(-1.0, 1.0)
                variant_text = self._modulate_word(token.word, mood_sig)
                variant_id = f"var_{int(time.time()*1000)}_{random.randint(0,9999)}"
                variant = LexicalVariant(
                    variant_id=variant_id,
                    base_expression=token.word,
                    variant_text=variant_text,
                    register=token.register,
                    mood_signature=mood_sig,
                    strength=0.1,
                    occurrences=1,
                )
                agent.variants[variant_id] = variant
                variants_created += 1
                agent.total_variants += 1
                if len(agent.variants) > self._MAX_VARIANTS_PER_AGENT:
                    oldest = min(agent.variants, key=lambda vid: agent.variants[vid].occurrences)
                    agent.variants.pop(oldest, None)
        self._stats["total_variants"] += variants_created
        self._record_event("phase_vary", {"variants_created": variants_created})
        return {"variants_created": variants_created}

    def _phase_crystallize(self) -> Dict[str, Any]:
        """Crystallize phase: recurring variants harden into preferences."""
        crystallized = 0
        for agent in self._agents.values():
            for variant in list(agent.variants.values()):
                variant.occurrences += 1
                if variant.occurrences >= self._CRYSTALLIZE_THRESHOLD:
                    # Find or create a preference for this register.
                    pref_key = f"pref_{variant.register.value}"
                    pref = agent.preferences.get(pref_key)
                    if pref is None:
                        pref = LexicalPreference(
                            preference_id=pref_key,
                            word_class=WordClass.NOUN,
                            register_affinity={variant.register.value: 0.3},
                            strength=0.2,
                        )
                        agent.preferences[pref_key] = pref
                        if len(agent.preferences) > self._MAX_PREFERENCES_PER_AGENT:
                            # Drop the weakest preference (not the default).
                            non_default = {
                                k: v for k, v in agent.preferences.items()
                                if k != "__default_register__"
                            }
                            if non_default:
                                weakest = min(non_default, key=lambda k: non_default[k].strength)
                                agent.preferences.pop(weakest, None)
                    if variant.variant_text not in pref.preferred_tokens:
                        pref.preferred_tokens.append(variant.variant_text)
                        if len(pref.preferred_tokens) > 12:
                            pref.preferred_tokens.pop(0)
                    pref.register_affinity[variant.register.value] = min(
                        1.0, pref.register_affinity.get(variant.register.value, 0.0) + 0.1
                    )
                    pref.strength = min(1.0, pref.strength + self._CRYSTALLIZE_STRENGTH_GAIN)
                    agent.voice_strength = min(1.0, agent.voice_strength + 0.03)
                    crystallized += 1
                    agent.total_crystallizations += 1
                    # Remove the variant once crystallized.
                    agent.variants.pop(variant.variant_id, None)
            # Update voice state based on strength.
            if agent.voice_strength >= self._SIGNATURE_STRENGTH_THRESHOLD and agent.voice_state == VoiceState.FORMING:
                agent.voice_state = VoiceState.DISTINCT
                agent.voice_signature = self._mint_signature(agent)
            elif agent.voice_strength >= 0.8 and agent.voice_state in (VoiceState.DISTINCT, VoiceState.RECONCILING):
                agent.voice_state = VoiceState.FORGED
        self._stats["total_crystallizations"] += crystallized
        self._record_event("phase_crystallize", {"crystallized": crystallized})
        return {"crystallized": crystallized}

    def _phase_drift(self) -> Dict[str, Any]:
        """Drift phase: dialect pressure moves the forged voice."""
        drifts = 0
        for agent in self._agents.values():
            if not agent.dialect_pressures:
                continue
            if agent.voice_state in (VoiceState.RAW, VoiceState.FORMING):
                continue
            total_drift = 0.0
            for pressure in agent.dialect_pressures:
                resistance = agent.voice_strength * self._RECONCILE_RESISTANCE
                effective = max(0.0, pressure.intensity - resistance)
                drift_amount = effective * self._DRIFT_RATE
                agent.dialect_drift = min(1.0, agent.dialect_drift + drift_amount)
                agent.reconciliation_tension = min(1.0, agent.reconciliation_tension + effective * 0.2)
                total_drift += drift_amount
                drifts += 1
            if agent.voice_state == VoiceState.DISTINCT and agent.dialect_drift > 0.2:
                agent.voice_state = VoiceState.DRIFTING
            elif agent.voice_state == VoiceState.FORGED and agent.dialect_drift > 0.4:
                agent.voice_state = VoiceState.DRIFTING
        self._stats["total_drifts"] += drifts
        self._record_event("phase_drift", {"drifts": drifts})
        return {"drifts": drifts}

    def _phase_reconcile(self) -> Dict[str, Any]:
        """Reconcile phase: tension between forged voice and social voice eases."""
        reconciliations = 0
        for agent in self._agents.values():
            if agent.reconciliation_tension <= 0.0:
                continue
            # Strong forged voices lose some tension by absorbing dialect.
            absorb = agent.voice_strength * 0.15
            resist = (1.0 - agent.voice_strength) * 0.05
            agent.reconciliation_tension = max(
                0.0, agent.reconciliation_tension - self._RECONCILE_TENSION_DECAY - absorb + resist
            )
            agent.reconciliation_tension = min(1.0, agent.reconciliation_tension)
            if agent.reconciliation_tension < 0.1:
                if agent.voice_state == VoiceState.DRIFTING:
                    # Drifting voices either recommit (forged) or settle (distinct).
                    if agent.voice_strength >= 0.7:
                        agent.voice_state = VoiceState.FORGED
                    else:
                        agent.voice_state = VoiceState.DISTINCT
                    agent.dialect_drift = max(0.0, agent.dialect_drift - 0.1)
                reconciliations += 1
        self._stats["total_reconciliations"] += reconciliations
        self._record_event("phase_reconcile", {"reconciliations": reconciliations})
        return {"reconciliations": reconciliations}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _modulate_word(self, word: str, mood: float) -> str:
        """Modulate a word by a mood signature to produce a variant."""
        prefixes = ["the ", "a ", "this ", "that "]
        suffixes = [" indeed", " perhaps", " always", " never", " again"]
        if mood > 0.5:
            return random.choice(prefixes) + word + random.choice(suffixes)
        elif mood < -0.5:
            return word + random.choice([" faltering", " broken", " weary"])
        else:
            return random.choice(prefixes) + word

    def _mint_signature(self, agent: LexicalAgent) -> str:
        """Mint a signature phrase capturing the agent's forged voice."""
        tokens_by_class: Dict[WordClass, List[str]] = {}
        for token in agent.tokens.values():
            tokens_by_class.setdefault(token.word_class, []).append(token.word)
        if not tokens_by_class:
            return ""
        # Pick the most-used class and compose a short phrase.
        best_class = max(tokens_by_class, key=lambda wc: len(tokens_by_class[wc]))
        words = tokens_by_class[best_class][:3]
        if len(words) >= 2:
            return f"{' '.join(words[:2])}"
        return words[0] if words else ""

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "voice_state": agent.voice_state.value,
                "voice_strength": agent.voice_strength,
                "dialect_drift": agent.dialect_drift,
                "reconciliation_tension": agent.reconciliation_tension,
                "voice_signature": agent.voice_signature,
                "total_tokens": len(agent.tokens),
                "total_variants": len(agent.variants),
                "total_preferences": len(agent.preferences),
                "total_utterances": agent.total_utterances,
                "total_crystallizations": agent.total_crystallizations,
            }

    def get_voice_signature(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "voice_signature": agent.voice_signature,
                "voice_strength": agent.voice_strength,
                "voice_state": agent.voice_state.value,
            }

    def get_preferences(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "preferences": [
                    {
                        "preference_id": p.preference_id,
                        "word_class": p.word_class.value,
                        "preferred_tokens": p.preferred_tokens,
                        "register_affinity": p.register_affinity,
                        "strength": p.strength,
                        "signature_phrase": p.signature_phrase,
                    }
                    for p in agent.preferences.values()
                ],
            }

    def get_tokens(self, agent_id: str, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            tokens = sorted(agent.tokens.values(), key=lambda t: t.last_used_at, reverse=True)[:limit]
            return {
                "agent_id": agent_id,
                "tokens": [
                    {
                        "token_id": t.token_id,
                        "word": t.word,
                        "word_class": t.word_class.value,
                        "register": t.register.value,
                        "emotional_valence": t.emotional_valence,
                        "usage_count": t.usage_count,
                    }
                    for t in tokens
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "agents": len(self._agents),
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic agents and run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_agents()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_agents(self) -> None:
        """Seed a small synthetic cast of agents with distinct registers."""
        seed_agents = [
            ("sim_bard", "poetic", WordClass.METAPHOR, [
                ("the moon limps home", 0.4),
                ("the moon drags its wounded light", 0.3),
                ("the moon limps home", 0.4),
                ("the moon drags its wounded light", 0.3),
            ]),
            ("sim_soldier", "martial", WordClass.VERB, [
                ("hold the line", 0.6),
                ("hold the line", 0.6),
                ("break their charge", 0.7),
                ("hold the line", 0.6),
            ]),
            ("sim_scholar", "formal", WordClass.NOUN, [
                ("the hypothesis", 0.1),
                ("the conclusion", 0.0),
                ("the hypothesis", 0.1),
                ("the conclusion", 0.0),
            ]),
        ]
        for agent_id, register, word_class, utterances in seed_agents:
            if agent_id in self._agents:
                continue
            self.register_agent(agent_id, default_register=register)
            for i, (text, valence) in enumerate(utterances):
                self.utter(agent_id, f"{agent_id}_tok_{i}", text, word_class,
                           LexicalRegister(register), emotional_valence=valence)
            self.apply_dialect_pressure(
                agent_id, "frontline_dialect", LexicalRegister.MARTIAL, intensity=0.4
            )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._agents.clear()
            self._events_log.clear()
            self._phase = LexicalPhase.UTTER
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
