"""
SparkLabs Backend - Emergent Grammar Engine Routes

REST endpoints for the Engine Emergent Grammar Engine.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterElementRequest(BaseModel):
    element_id: str
    label: str
    element_type: str = "matter"    # matter/energy/life/mind/spirit/social/narrative/temporal/spatial/abstract
    properties: Optional[Dict[str, float]] = None


class ObserveInteractionRequest(BaseModel):
    element_a_id: str
    element_b_id: str
    interaction_type: str = "creates"  # creates/transforms/destroys/combines/repels/attracts/modifies/triggers
    result_description: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/emergent-grammar/elements")
async def grammar_register_element(req: RegisterElementRequest):
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine, ElementType,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    try:
        elem_type = ElementType(req.element_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid element_type: {req.element_type}"}
    result = engine.register_element(
        element_id=req.element_id,
        label=req.label,
        element_type=elem_type,
        properties=req.properties,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/emergent-grammar/interactions")
async def grammar_observe_interaction(req: ObserveInteractionRequest):
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine, InteractionType,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    try:
        inter_type = InteractionType(req.interaction_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid interaction_type: {req.interaction_type}"}
    result = engine.observe_interaction(
        element_a_id=req.element_a_id,
        element_b_id=req.element_b_id,
        interaction_type=inter_type,
        result_description=req.result_description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emergent-grammar/rules")
async def grammar_get_all_rules():
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.get_all_rules()}


@router.get("/emergent-grammar/rules/{rule_id}")
async def grammar_get_rule(rule_id: str):
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    result = engine.get_rule(rule_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emergent-grammar/grammar-sets")
async def grammar_get_grammar_sets():
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.get_grammar_sets()}


@router.get("/emergent-grammar/interactions")
async def grammar_get_interactions(limit: int = 50):
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.get_interactions(limit=limit)}


@router.get("/emergent-grammar/elements")
async def grammar_get_elements():
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.get_elements()}


@router.get("/emergent-grammar/events")
async def grammar_get_events(limit: int = 50):
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.get_events_log(limit=limit)}


@router.get("/emergent-grammar/status")
async def grammar_get_status():
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.get_status()}


@router.post("/emergent-grammar/cycle")
async def grammar_cycle():
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.cycle()}


@router.post("/emergent-grammar/simulate")
async def grammar_simulate(req: SimulateRequest):
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.simulate(cycles=req.cycles)}


@router.post("/emergent-grammar/reset")
async def grammar_reset():
    from sparkai.engine.engine_emergent_grammar_engine import (
        EngineEmergentGrammarEngine,
    )
    engine = EngineEmergentGrammarEngine.get_instance()
    return {"status": "ok", "data": engine.reset()}
