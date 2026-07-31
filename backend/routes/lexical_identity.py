"""
SparkLabs Backend - Lexical Identity Forge Routes

REST endpoints for the Agent Lexical Identity Forge.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str
    default_register: str = "casual"  # formal/casual/intimate/martial/poetic/vulgar/arcane/colloquial


class UtterRequest(BaseModel):
    agent_id: str
    token_id: str
    word: str
    word_class: str = "noun"           # noun/verb/adjective/adverb/interjection/metaphor/oath
    register: str = "casual"
    emotional_valence: float = 0.0     # -1.0 to 1.0


class DialectPressureRequest(BaseModel):
    agent_id: str
    source: str
    register: str = "colloquial"
    intensity: float = 0.3
    tokens_introduced: Optional[List[str]] = None


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/lexical-identity/agents")
async def lexical_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    result = forge.register_agent(req.agent_id, default_register=req.default_register)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/lexical-identity/utter")
async def lexical_utter(req: UtterRequest):
    from sparkai.agent.agent_lexical_identity_forge import (
        AgentLexicalIdentityForge, WordClass, LexicalRegister,
    )
    forge = AgentLexicalIdentityForge.get_instance()
    try:
        word_class = WordClass(req.word_class)
    except ValueError:
        return {"status": "error", "detail": f"Invalid word_class: {req.word_class}"}
    try:
        register = LexicalRegister(req.register)
    except ValueError:
        return {"status": "error", "detail": f"Invalid register: {req.register}"}
    result = forge.utter(
        agent_id=req.agent_id,
        token_id=req.token_id,
        word=req.word,
        word_class=word_class,
        register=register,
        emotional_valence=req.emotional_valence,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/lexical-identity/dialect-pressure")
async def lexical_apply_dialect_pressure(req: DialectPressureRequest):
    from sparkai.agent.agent_lexical_identity_forge import (
        AgentLexicalIdentityForge, LexicalRegister,
    )
    forge = AgentLexicalIdentityForge.get_instance()
    try:
        register = LexicalRegister(req.register)
    except ValueError:
        return {"status": "error", "detail": f"Invalid register: {req.register}"}
    result = forge.apply_dialect_pressure(
        agent_id=req.agent_id,
        source=req.source,
        register=register,
        intensity=req.intensity,
        tokens_introduced=req.tokens_introduced,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/lexical-identity/agents/{agent_id}")
async def lexical_get_agent_state(agent_id: str):
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    result = forge.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/lexical-identity/agents/{agent_id}/voice")
async def lexical_get_voice_signature(agent_id: str):
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    result = forge.get_voice_signature(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/lexical-identity/agents/{agent_id}/preferences")
async def lexical_get_preferences(agent_id: str):
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    result = forge.get_preferences(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/lexical-identity/agents/{agent_id}/tokens")
async def lexical_get_tokens(agent_id: str, limit: int = 50):
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    result = forge.get_tokens(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/lexical-identity/events")
async def lexical_get_events(limit: int = 50):
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    return {"status": "ok", "data": forge.get_events_log(limit=limit)}


@router.get("/lexical-identity/status")
async def lexical_get_status():
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    return {"status": "ok", "data": forge.get_status()}


@router.post("/lexical-identity/cycle")
async def lexical_cycle():
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    return {"status": "ok", "data": forge.cycle()}


@router.post("/lexical-identity/simulate")
async def lexical_simulate(req: SimulateRequest):
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    return {"status": "ok", "data": forge.simulate(cycles=req.cycles)}


@router.post("/lexical-identity/reset")
async def lexical_reset():
    from sparkai.agent.agent_lexical_identity_forge import AgentLexicalIdentityForge
    forge = AgentLexicalIdentityForge.get_instance()
    return {"status": "ok", "data": forge.reset()}
