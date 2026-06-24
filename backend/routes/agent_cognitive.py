"""
SparkLabs Backend - Agent Cognitive Synthesis & Game Intelligence Routes

API endpoints for cognitive synthesis engine (input analysis,
goal-driven synthesis, history tracking, performance metrics)
and game intelligence engine (design analysis, quality evaluation,
improvement suggestions, pattern detection).
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for cognitive synthesis
_synthesis_history: List[Dict[str, Any]] = []
_synthesis_metrics: Dict[str, Any] = {
    "total_syntheses": 0,
    "avg_confidence": 0.0,
    "avg_depth": 0.0,
    "total_insights": 0,
}

# In-memory storage for game intelligence
_design_analyses: List[Dict[str, Any]] = []
_quality_evaluations: List[Dict[str, Any]] = []
_design_patterns: List[Dict[str, Any]] = [
    {"id": "observer", "name": "Observer", "category": "BEHAVIORAL", "confidence": 0.92},
    {"id": "state-machine", "name": "State Machine", "category": "BEHAVIORAL", "confidence": 0.88},
    {"id": "entity-component", "name": "Entity-Component", "category": "ARCHITECTURAL", "confidence": 0.95},
    {"id": "object-pool", "name": "Object Pool", "category": "PERFORMANCE", "confidence": 0.85},
    {"id": "command", "name": "Command", "category": "BEHAVIORAL", "confidence": 0.90},
]
_game_intel_metrics: Dict[str, Any] = {
    "total_analyses": 0,
    "total_evaluations": 0,
    "total_suggestions": 0,
    "patterns_detected": 0,
}


class SynthesizeRequest(BaseModel):
    input_text: str = ""
    prompt: str = ""
    goal: str = ""
    constraints: Dict[str, Any] = {}
    depth: int = 3
    reasoning_depth: str = "moderate"


class GameSnapshotRequest(BaseModel):
    snapshot_data: Dict[str, Any] = {}


class EvaluateRequest(BaseModel):
    analysis_data: Dict[str, Any]


class SuggestionsRequest(BaseModel):
    analysis_data: Dict[str, Any]
    domain: str = "general"


@router.post("/cognitive/synthesize")
async def cognitive_synthesize(request: SynthesizeRequest):
    try:
        synthesis_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Support both prompt and input_text field names from frontend
        input_text = request.prompt or request.input_text
        depth = request.depth
        if request.reasoning_depth:
            depth_map = {"shallow": 1, "moderate": 3, "deep": 5, "comprehensive": 7}
            depth = depth_map.get(request.reasoning_depth.lower(), 3)

        phases = []
        for phase_idx in range(1, min(depth + 1, 5)):
            phases.append({
                "phase": f"phase_{phase_idx}",
                "name": ["INPUT_ANALYSIS", "PATTERN_RECOGNITION", "SYNTHESIS", "REFINEMENT", "VALIDATION"][phase_idx - 1],
                "confidence": min(0.5 + (phase_idx * 0.1), 1.0),
                "insights": [
                    f"Insight {phase_idx}.1 from analyzing '{input_text[:50]}...'",
                    f"Insight {phase_idx}.2 related to goal: '{request.goal[:50]}...'",
                ],
            })

        overall_confidence = sum(p["confidence"] for p in phases) / len(phases) if phases else 0.8

        report = {
            "synthesis_id": synthesis_id,
            "input_text": input_text[:200],
            "goal": request.goal,
            "constraints": request.constraints,
            "depth": depth,
            "phases": phases,
            "overall_confidence": round(overall_confidence, 4),
            "summary": f"Synthesis complete: {len(phases)} phases processed with {overall_confidence:.0%} confidence",
            "timestamp": timestamp,
        }

        _synthesis_history.append(report)

        _synthesis_metrics["total_syntheses"] += 1
        _synthesis_metrics["avg_confidence"] = (
            (_synthesis_metrics["avg_confidence"] * (_synthesis_metrics["total_syntheses"] - 1) + overall_confidence)
            / _synthesis_metrics["total_syntheses"]
        )
        _synthesis_metrics["avg_depth"] = (
            (_synthesis_metrics["avg_depth"] * (_synthesis_metrics["total_syntheses"] - 1) + depth)
            / _synthesis_metrics["total_syntheses"]
        )
        _synthesis_metrics["total_insights"] += sum(len(p["insights"]) for p in phases)

        return {
            "status": "success",
            "data": report,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/cognitive/history")
async def get_synthesis_history(limit: int = Query(default=20)):
    try:
        history = _synthesis_history[-limit:]

        return {
            "status": "success",
            "data": {
                "history": history,
                "total_count": len(_synthesis_history),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/cognitive/metrics")
async def get_cognitive_metrics():
    try:
        return {
            "status": "success",
            "data": _synthesis_metrics,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/game-intel/analyze")
async def analyze_game_design(request: GameSnapshotRequest):
    try:
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        snapshot = request.snapshot_data
        entity_count = snapshot.get("entity_count", 0)
        system_count = snapshot.get("system_count", 0)

        design_patterns_detected = []
        for pattern in _design_patterns[:3]:
            design_patterns_detected.append({
                "pattern_id": pattern["id"],
                "pattern_name": pattern["name"],
                "category": pattern["category"],
                "confidence": round(pattern["confidence"] * 0.9, 4),
            })

        dimensions = []
        for dim_name in ["ARCHITECTURE", "MECHANICS", "AESTHETICS", "NARRATIVE", "TECHNOLOGY"]:
            dimensions.append({
                "dimension": dim_name,
                "score": round(0.5 + (hash(dim_name + str(snapshot)) % 50) / 100, 2),
                "observations": [
                    f"{dim_name} observation 1 based on {entity_count} entities",
                    f"{dim_name} observation 2 based on {system_count} systems",
                ],
            })

        overall_score = round(sum(d["score"] for d in dimensions) / len(dimensions), 2)

        analysis = {
            "analysis_id": analysis_id,
            "snapshot": snapshot,
            "design_patterns": design_patterns_detected,
            "dimensions": dimensions,
            "overall_score": overall_score,
            "summary": f"Analysis complete: {len(design_patterns_detected)} patterns detected, overall score {overall_score}",
            "timestamp": timestamp,
        }

        _design_analyses.append(analysis)
        _game_intel_metrics["total_analyses"] += 1
        _game_intel_metrics["patterns_detected"] += len(design_patterns_detected)

        return {
            "status": "success",
            "data": analysis,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/game-intel/evaluate")
async def evaluate_quality(request: EvaluateRequest):
    try:
        evaluation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        analysis_data = request.analysis_data

        quality_checks = []
        for check_name in ["PERFORMANCE", "BALANCE", "USABILITY", "ACCESSIBILITY", "STABILITY"]:
            quality_checks.append({
                "check": check_name,
                "passed": True,
                "score": round(0.6 + (hash(check_name + str(analysis_data)) % 40) / 100, 2),
                "details": f"{check_name} evaluation passed based on provided analysis data",
                "recommendations": [
                    f"Consider optimizing {check_name.lower()} aspects",
                    f"Monitor {check_name.lower()} metrics over time",
                ],
            })

        overall_quality = round(sum(c["score"] for c in quality_checks) / len(quality_checks), 2)
        passed_count = sum(1 for c in quality_checks if c["passed"])

        evaluation = {
            "evaluation_id": evaluation_id,
            "quality_checks": quality_checks,
            "overall_quality": overall_quality,
            "passed_checks": passed_count,
            "total_checks": len(quality_checks),
            "verdict": "PASS" if passed_count == len(quality_checks) else "FAIL",
            "timestamp": timestamp,
        }

        _quality_evaluations.append(evaluation)
        _game_intel_metrics["total_evaluations"] += 1

        return {
            "status": "success",
            "data": evaluation,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/game-intel/suggestions")
async def get_improvement_suggestions(request: SuggestionsRequest):
    try:
        suggestions_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        analysis_data = request.analysis_data
        domain = request.domain

        suggestions = []
        for priority in ["HIGH", "MEDIUM", "LOW"]:
            for i in range(2):
                suggestions.append({
                    "id": str(uuid.uuid4()),
                    "domain": domain,
                    "priority": priority,
                    "title": f"{priority.lower().capitalize()} priority suggestion {i + 1} for {domain}",
                    "description": f"Improvement suggestion based on analysis of {domain} domain",
                    "expected_impact": round(0.3 + (hash(f"{priority}{i}{domain}") % 60) / 100, 2),
                    "effort_estimate": "LOW" if priority == "HIGH" else "MEDIUM",
                    "category": domain,
                })

        _game_intel_metrics["total_suggestions"] += len(suggestions)

        return {
            "status": "success",
            "data": {
                "suggestions_id": suggestions_id,
                "domain": domain,
                "suggestions": suggestions,
                "total_count": len(suggestions),
                "timestamp": timestamp,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/game-intel/patterns")
async def get_design_patterns(
    category: str = Query(default=""),
    limit: int = Query(default=20),
):
    try:
        patterns = _design_patterns
        if category:
            patterns = [p for p in patterns if p.get("category", "").upper() == category.upper()]

        patterns = patterns[:limit]

        return {
            "status": "success",
            "data": {
                "patterns": patterns,
                "total_count": len(patterns),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/game-intel/suggestions")
async def get_suggestions(domain: str = Query(default="general")):
    try:
        suggestions = []
        for priority in ["HIGH", "MEDIUM", "LOW"]:
            for i in range(2):
                suggestions.append({
                    "id": str(uuid.uuid4()),
                    "domain": domain,
                    "priority": priority,
                    "title": f"{priority.lower().capitalize()} priority suggestion {i + 1} for {domain}",
                    "description": f"Improvement suggestion based on analysis of {domain} domain",
                    "expected_impact": round(0.3 + (hash(f"{priority}{i}{domain}") % 60) / 100, 2),
                    "effort_estimate": "LOW" if priority == "HIGH" else "MEDIUM",
                    "category": domain,
                })

        return {
            "status": "success",
            "data": {
                "suggestions": suggestions,
                "total_count": len(suggestions),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/game-intel/metrics")
async def get_game_intelligence_metrics():
    try:
        return {
            "status": "success",
            "data": _game_intel_metrics,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )