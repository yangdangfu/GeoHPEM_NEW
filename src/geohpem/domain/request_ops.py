from __future__ import annotations

import copy
from typing import Any

from geohpem.project.normalize import find_stage_index_by_uid
from geohpem.util.ids import new_uid


def apply_stage_patch_by_uid(request: dict[str, Any], stage_uid: str, patch: dict[str, Any]) -> dict[str, Any]:
    """
    Pure-ish helper: returns a deep-copied request with patch applied to the stage with given uid.
    """
    req = copy.deepcopy(request)
    idx = find_stage_index_by_uid(req, stage_uid)
    if idx is None:
        raise KeyError(f"Stage uid not found: {stage_uid}")
    stages = req.get("stages", [])
    if not isinstance(stages, list) or idx < 0 or idx >= len(stages):
        raise IndexError(idx)
    stage = stages[idx]
    if not isinstance(stage, dict):
        raise TypeError("stage is not an object")
    stage.update(patch)
    return req


def apply_stage_patch_by_index(request: dict[str, Any], index: int, patch: dict[str, Any]) -> dict[str, Any]:
    req = copy.deepcopy(request)
    stages = req.get("stages", [])
    if not isinstance(stages, list) or index < 0 or index >= len(stages):
        raise IndexError(index)
    stage = stages[index]
    if not isinstance(stage, dict):
        raise TypeError("stage is not an object")
    stage.update(patch)
    return req


def set_model_mode(request: dict[str, Any], mode: str) -> dict[str, Any]:
    req = copy.deepcopy(request)
    model = req.setdefault("model", {})
    if not isinstance(model, dict):
        model = {}
        req["model"] = model
    model["mode"] = str(mode)
    return req


def set_gravity(request: dict[str, Any], gx: float, gy: float) -> dict[str, Any]:
    req = copy.deepcopy(request)
    model = req.setdefault("model", {})
    if not isinstance(model, dict):
        model = {}
        req["model"] = model
    model["gravity"] = [float(gx), float(gy)]
    return req


def set_model(request: dict[str, Any], *, mode: str | None = None, gravity: tuple[float, float] | None = None) -> dict[str, Any]:
    req = copy.deepcopy(request)
    model_obj = req.setdefault("model", {})
    if not isinstance(model_obj, dict):
        model_obj = {}
        req["model"] = model_obj
    if mode is not None:
        model_obj["mode"] = str(mode)
    if gravity is not None:
        gx, gy = gravity
        model_obj["gravity"] = [float(gx), float(gy)]
    return req


def upsert_material(request: dict[str, Any], material_id: str, model_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    req = copy.deepcopy(request)
    mats = req.setdefault("materials", {})
    if not isinstance(mats, dict):
        mats = {}
        req["materials"] = mats
    existing = mats.get(material_id)
    uid = None
    if isinstance(existing, dict):
        uid = existing.get("uid")
    payload: dict[str, Any] = {"model_name": str(model_name), "parameters": dict(parameters)}
    if uid:
        payload["uid"] = uid
    else:
        payload["uid"] = new_uid("mat")
    mats[str(material_id)] = payload
    return req


def delete_material(request: dict[str, Any], material_id: str) -> dict[str, Any]:
    req = copy.deepcopy(request)
    mats = req.get("materials", {})
    if not isinstance(mats, dict):
        return req
    mats = dict(mats)
    mats.pop(material_id, None)
    req["materials"] = mats
    return req


def set_assignments(request: dict[str, Any], assignments: list[dict[str, Any]]) -> dict[str, Any]:
    req = copy.deepcopy(request)
    cleaned: list[dict[str, Any]] = []
    for it in assignments:
        if not isinstance(it, dict):
            continue
        obj = dict(it)
        uid = obj.get("uid")
        if not isinstance(uid, str) or not uid:
            obj["uid"] = new_uid("assign")
        cleaned.append(obj)
    req["assignments"] = cleaned
    return req


def set_global_output_requests(request: dict[str, Any], output_requests: list[dict[str, Any]]) -> dict[str, Any]:
    req = copy.deepcopy(request)
    cleaned: list[dict[str, Any]] = []
    for it in output_requests:
        if not isinstance(it, dict):
            continue
        obj = dict(it)
        uid = obj.get("uid")
        if not isinstance(uid, str) or not uid:
            obj["uid"] = new_uid("outreq")
        cleaned.append(obj)
    req["output_requests"] = cleaned
    return req


def _regen_nested_uids(stage: dict[str, Any]) -> None:
    for key, prefix in (("bcs", "bc"), ("loads", "load"), ("output_requests", "outreq")):
        items = stage.get(key)
        if not isinstance(items, list):
            continue
        for it in items:
            if isinstance(it, dict):
                it["uid"] = new_uid(prefix)


def add_stage(request: dict[str, Any], *, copy_from_index: int | None = None) -> tuple[dict[str, Any], int]:
    """
    Returns (new_request, new_stage_index).

    Note: stage.uid and nested item uids are always regenerated for copied stages.
    """
    req = copy.deepcopy(request)
    stages = req.setdefault("stages", [])
    if not isinstance(stages, list):
        stages = []
        req["stages"] = stages

    if copy_from_index is None:
        new_stage: dict[str, Any] = {
            "id": f"stage_{len(stages)+1}",
            "uid": new_uid("stage"),
            "analysis_type": "static",
            "num_steps": 1,
            "bcs": [],
            "loads": [],
            "output_requests": [],
        }
    else:
        if copy_from_index < 0 or copy_from_index >= len(stages):
            raise IndexError(copy_from_index)
        src = stages[copy_from_index]
        if not isinstance(src, dict):
            raise TypeError("stage is not an object")
        new_stage = copy.deepcopy(src)
        new_stage["id"] = f"{new_stage.get('id','stage')}_copy"
        new_stage["uid"] = new_uid("stage")
        _regen_nested_uids(new_stage)

    stages.append(new_stage)
    return req, len(stages) - 1


def delete_stage(request: dict[str, Any], index: int) -> dict[str, Any]:
    req = copy.deepcopy(request)
    stages = req.get("stages", [])
    if not isinstance(stages, list):
        return req
    if len(stages) <= 1:
        raise ValueError("Cannot delete the last stage")
    if index < 0 or index >= len(stages):
        raise IndexError(index)
    stages.pop(index)
    return req


def set_geometry(request: dict[str, Any], geometry: dict[str, Any] | None) -> dict[str, Any]:
    req = copy.deepcopy(request)
    if geometry is None:
        req.pop("geometry", None)
    else:
        req["geometry"] = geometry
    return req
