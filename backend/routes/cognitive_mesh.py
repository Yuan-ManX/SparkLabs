"""
SparkLabs Backend - Cognitive Mesh Routes

REST API for the AgentCognitiveMesh and EngineIntelligenceSurface.
These two modules form the bidirectional intelligence fabric between
the AI agent layer and the game engine layer.

Routes:
  Cognitive Mesh (/api/agent/cognitive-mesh/...):
    GET  /status              - Get mesh status
    GET  /nodes               - List all mesh nodes
    GET  /signals             - Get recent signals
    POST /emit                - Emit a cognitive signal
    POST /cycle               - Run a single cognitive cycle
    POST /simulate            - Simulate traffic for testing
    GET  /intelligence        - Get learned routing intelligence
    POST /routing-rules       - Add a routing rule
    DELETE /routing-rules/{id} - Remove a routing rule
    POST /reset               - Reset the mesh

  Intelligence Surface (/api/agent/intelligence-surface/...):
    GET  /surface/status      - Get surface status
    GET  /surface/capabilities - List engine capabilities
    GET  /surface/capabilities/{id} - Get a specific capability
    POST /surface/intent      - Submit a semantic intent
    GET  /surface/intents     - Get recent intents
    POST /surface/simulate    - Simulate intents for testing
    POST /surface/reset       - Reset the surface
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class EmitSignalRequest(BaseModel):
    signal_type: str  # anomaly, opportunity, request, decision, feedback, telemetry, alert
    category: str
    source_node: str
    payload: Optional[Dict[str, Any]] = None
    priority: str = "normal"  # low, normal, high, urgent, critical
    target_node: Optional[str] = None


class AddRoutingRuleRequest(BaseModel):
    rule_id: str
    target_node_id: str
    signal_type: Optional[str] = None
    category: Optional[str] = None
    priority_boost: float = 0.0


class SubmitIntentRequest(BaseModel):
    action: str
    target: str
    parameters: Optional[Dict[str, Any]] = None
    description: str = ""


class SimulateRequest(BaseModel):
    count: int = 10


# ---------------------------------------------------------------------------
# Cognitive Mesh Endpoints
# ---------------------------------------------------------------------------

def _mesh():
    from sparkai.agent.agent_cognitive_mesh import AgentCognitiveMesh
    return AgentCognitiveMesh.get_instance()


@router.get("/cognitive-mesh/status")
async def get_mesh_status():
    """Get the cognitive mesh status."""
    return {"status": "ok", "data": _mesh().get_status()}


@router.get("/cognitive-mesh/nodes")
async def get_mesh_nodes():
    """List all mesh nodes."""
    return {"status": "ok", "data": _mesh().get_nodes()}


@router.get("/cognitive-mesh/signals")
async def get_mesh_signals(limit: int = 20):
    """Get recent signals."""
    return {"status": "ok", "data": _mesh().get_recent_signals(limit)}


@router.post("/cognitive-mesh/emit")
async def emit_signal(req: EmitSignalRequest):
    """Emit a cognitive signal into the mesh."""
    from sparkai.agent.agent_cognitive_mesh import SignalType, SignalPriority
    try:
        st = SignalType(req.signal_type)
    except ValueError:
        return {"status": "error", "error": f"Invalid signal_type: {req.signal_type}"}
    try:
        priority = SignalPriority[req.priority.upper()]
    except KeyError:
        priority = SignalPriority.NORMAL
    signal_id = _mesh().emit_signal(
        st, req.category, req.source_node, req.payload,
        priority, req.target_node,
    )
    return {"status": "ok", "data": {"signal_id": signal_id}}


@router.post("/cognitive-mesh/cycle")
async def run_mesh_cycle():
    """Run a single cognitive mesh cycle."""
    result = _mesh().run_cycle()
    return {"status": "ok", "data": result}


@router.post("/cognitive-mesh/simulate")
async def simulate_mesh_traffic(req: SimulateRequest):
    """Simulate cognitive signals for testing."""
    result = _mesh().simulate_traffic(req.count)
    return {"status": "ok", "data": result}


@router.get("/cognitive-mesh/intelligence")
async def get_routing_intelligence():
    """Get the learned routing intelligence."""
    return {"status": "ok", "data": _mesh().get_routing_intelligence()}


@router.post("/cognitive-mesh/routing-rules")
async def add_routing_rule(req: AddRoutingRuleRequest):
    """Add a custom routing rule."""
    success = _mesh().add_routing_rule(
        req.rule_id, req.target_node_id,
        req.signal_type, req.category, req.priority_boost,
    )
    return {"status": "ok" if success else "error", "data": {"added": success}}


@router.delete("/cognitive-mesh/routing-rules/{rule_id}")
async def remove_routing_rule(rule_id: str):
    """Remove a routing rule."""
    success = _mesh().remove_routing_rule(rule_id)
    return {"status": "ok" if success else "error", "data": {"removed": success}}


@router.post("/cognitive-mesh/reset")
async def reset_mesh():
    """Reset the cognitive mesh state."""
    _mesh().reset()
    return {"status": "ok", "data": {"message": "Cognitive mesh reset"}}


# ---------------------------------------------------------------------------
# Intelligence Surface Endpoints
# ---------------------------------------------------------------------------

def _surface():
    from sparkai.engine.engine_intelligence_surface import EngineIntelligenceSurface
    return EngineIntelligenceSurface.get_instance()


@router.get("/intelligence-surface/status")
async def get_surface_status():
    """Get the intelligence surface status."""
    return {"status": "ok", "data": _surface().get_status()}


@router.get("/intelligence-surface/capabilities")
async def get_capabilities(domain: Optional[str] = None):
    """List engine capabilities, optionally filtered by domain."""
    return {"status": "ok", "data": _surface().get_capabilities(domain)}


@router.get("/intelligence-surface/capabilities/{cap_id}")
async def get_capability(cap_id: str):
    """Get a specific capability by ID."""
    cap = _surface().get_capability(cap_id)
    if cap is None:
        return {"status": "error", "error": f"Capability {cap_id} not found"}
    return {"status": "ok", "data": cap}


@router.post("/intelligence-surface/intent")
async def submit_intent(req: SubmitIntentRequest):
    """Submit a semantic intent to the engine."""
    result = _surface().submit_intent(
        req.action, req.target, req.parameters, req.description,
    )
    return {"status": "ok", "data": result}


@router.get("/intelligence-surface/intents")
async def get_recent_intents(limit: int = 20):
    """Get recent intents."""
    return {"status": "ok", "data": _surface().get_recent_intents(limit)}


@router.post("/intelligence-surface/simulate")
async def simulate_intents(req: SimulateRequest):
    """Simulate semantic intents for testing."""
    result = _surface().simulate_intents(req.count)
    return {"status": "ok", "data": result}


@router.post("/intelligence-surface/reset")
async def reset_surface():
    """Reset the intelligence surface state."""
    _surface().reset()
    return {"status": "ok", "data": {"message": "Intelligence surface reset"}}
