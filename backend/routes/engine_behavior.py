"""
SparkLabs Backend - Engine Behavior Routes

API endpoints for behavior composer and asset compiler
engines including behavior template management,
instance creation, composition, and asset compilation.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------------

_templates: Dict[str, Dict[str, Any]] = {}
_instances: Dict[str, Dict[str, Any]] = {}
_compositions: Dict[str, Dict[str, Any]] = {}
_attachments: Dict[str, List[Dict[str, Any]]] = {}

_source_assets: Dict[str, Dict[str, Any]] = {}
_compiled_assets: Dict[str, Dict[str, Any]] = {}
_bundles: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request models - Behavior Composer
# ---------------------------------------------------------------------------

class TemplateCreateRequest(BaseModel):
    name: str
    category: str = "general"
    description: str = ""
    parameters: Optional[Dict[str, Any]] = None
    update_order: int = 0


class InstanceCreateRequest(BaseModel):
    template_id: str
    object_id: str
    params: Optional[Dict[str, Any]] = None


class AttachRequest(BaseModel):
    object_id: str
    instance_id: str
    slot_name: str = "default"


class DetachRequest(BaseModel):
    object_id: str
    instance_id: str


# ---------------------------------------------------------------------------
# Request models - Asset Compiler
# ---------------------------------------------------------------------------

class AssetImportRequest(BaseModel):
    source_path: str
    asset_type: str = "generic"


class CompileRequest(BaseModel):
    source_id: str


class BundleBuildRequest(BaseModel):
    name: str
    asset_ids: List[str] = []
    strategy: str = "default"


# ---------------------------------------------------------------------------
# Behavior Composer Endpoints
# ---------------------------------------------------------------------------

@router.post("/behavior/template")
async def register_template(request: TemplateCreateRequest):
    try:
        template_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        template = {
            "id": template_id,
            "name": request.name,
            "category": request.category,
            "description": request.description,
            "parameters": request.parameters or {},
            "update_order": request.update_order,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        _templates[template_id] = template

        return {"status": "success", "data": template}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/behavior/templates")
async def list_templates(category: Optional[str] = Query(None)):
    try:
        templates = list(_templates.values())
        if category:
            templates = [t for t in templates if t.get("category") == category]

        return {
            "status": "success",
            "data": {
                "templates": templates,
                "total_count": len(templates),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/behavior/instance")
async def create_instance(request: InstanceCreateRequest):
    try:
        template = _templates.get(request.template_id)
        if not template:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Template not found"},
            )

        instance_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        instance = {
            "id": instance_id,
            "template_id": request.template_id,
            "object_id": request.object_id,
            "params": request.params or {},
            "template_name": template["name"],
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        _instances[instance_id] = instance

        return {"status": "success", "data": instance}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/behavior/attach")
async def attach_behavior(request: AttachRequest):
    try:
        instance = _instances.get(request.instance_id)
        if not instance:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Instance not found"},
            )

        timestamp = datetime.utcnow().isoformat()
        attachment = {
            "object_id": request.object_id,
            "instance_id": request.instance_id,
            "slot_name": request.slot_name,
            "attached_at": timestamp,
        }

        if request.object_id not in _attachments:
            _attachments[request.object_id] = []
        _attachments[request.object_id].append(attachment)

        return {"status": "success", "data": attachment}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/behavior/detach")
async def detach_behavior(request: DetachRequest):
    try:
        if request.object_id not in _attachments:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "No attachments found for object"},
            )

        attachments = _attachments[request.object_id]
        _attachments[request.object_id] = [
            a for a in attachments if a["instance_id"] != request.instance_id
        ]

        return {
            "status": "success",
            "data": {
                "object_id": request.object_id,
                "instance_id": request.instance_id,
                "detached": True,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/behavior/composition/{object_id}")
async def get_composition(object_id: str):
    try:
        obj_attachments = _attachments.get(object_id, [])
        attached_instances = []
        for att in obj_attachments:
            inst = _instances.get(att["instance_id"])
            if inst:
                attached_instances.append({
                    "instance": inst,
                    "slot_name": att["slot_name"],
                    "attached_at": att["attached_at"],
                })

        composition = {
            "object_id": object_id,
            "behavior_count": len(attached_instances),
            "behaviors": attached_instances,
            "generated_at": datetime.utcnow().isoformat(),
        }

        return {"status": "success", "data": composition}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/behavior/report/{object_id}")
async def get_behavior_report(object_id: str):
    try:
        obj_attachments = _attachments.get(object_id, [])
        instance_details = []
        for att in obj_attachments:
            inst = _instances.get(att["instance_id"])
            if inst:
                template = _templates.get(inst["template_id"])
                instance_details.append({
                    "instance_id": inst["id"],
                    "template_name": template["name"] if template else "unknown",
                    "category": template["category"] if template else "unknown",
                    "slot_name": att["slot_name"],
                    "params": inst["params"],
                })

        report = {
            "object_id": object_id,
            "total_behaviors": len(instance_details),
            "behaviors": instance_details,
            "generated_at": datetime.utcnow().isoformat(),
        }

        return {"status": "success", "data": report}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/behavior/stats")
async def get_behavior_composer_stats():
    try:
        stats = {
            "templates_count": len(_templates),
            "instances_count": len(_instances),
            "objects_with_behaviors": len(_attachments),
            "total_attachments": sum(len(v) for v in _attachments.values()),
            "generated_at": datetime.utcnow().isoformat(),
        }

        return {"status": "success", "data": stats}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# ---------------------------------------------------------------------------
# Asset Compiler Endpoints
# ---------------------------------------------------------------------------

@router.post("/asset/import")
async def import_asset(request: AssetImportRequest):
    try:
        source_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        source = {
            "id": source_id,
            "source_path": request.source_path,
            "asset_type": request.asset_type,
            "imported_at": timestamp,
            "compiled": False,
        }

        _source_assets[source_id] = source

        return {"status": "success", "data": source}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/asset/compile")
async def compile_asset(request: CompileRequest):
    try:
        source = _source_assets.get(request.source_id)
        if not source:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Source asset not found"},
            )

        timestamp = datetime.utcnow().isoformat()
        compile_id = str(uuid.uuid4())

        compiled = {
            "id": compile_id,
            "source_id": request.source_id,
            "source_path": source["source_path"],
            "asset_type": source["asset_type"],
            "status": "completed",
            "compiled_at": timestamp,
            "output_size": 0,
        }

        _compiled_assets[compile_id] = compiled
        source["compiled"] = True

        return {"status": "success", "data": compiled}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/asset/bundle")
async def build_bundle(request: BundleBuildRequest):
    try:
        bundle_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        asset_list = []
        for aid in request.asset_ids:
            asset = _compiled_assets.get(aid) or _source_assets.get(aid)
            if asset:
                asset_list.append(asset)

        bundle = {
            "id": bundle_id,
            "name": request.name,
            "strategy": request.strategy,
            "asset_ids": request.asset_ids,
            "asset_count": len(asset_list),
            "assets": asset_list,
            "created_at": timestamp,
        }

        _bundles[bundle_id] = bundle

        return {"status": "success", "data": bundle}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/asset/stats")
async def get_compiler_stats():
    try:
        stats = {
            "source_count": len(_source_assets),
            "compiled_count": len(_compiled_assets),
            "bundle_count": len(_bundles),
            "compilation_rate": (
                len(_compiled_assets) / len(_source_assets)
                if _source_assets else 0
            ),
            "generated_at": datetime.utcnow().isoformat(),
        }

        return {"status": "success", "data": stats}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/asset/sources")
async def list_sources():
    try:
        sources = list(_source_assets.values())
        return {
            "status": "success",
            "data": {
                "sources": sources,
                "total_count": len(sources),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/asset/bundles")
async def list_bundles():
    try:
        bundles = list(_bundles.values())
        return {
            "status": "success",
            "data": {
                "bundles": bundles,
                "total_count": len(bundles),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )