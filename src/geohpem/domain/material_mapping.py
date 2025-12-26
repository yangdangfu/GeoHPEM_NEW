from __future__ import annotations

import copy
from typing import Any

from geohpem.domain import material_catalog as mc


def _get_path(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def map_material_for_solver(material: dict[str, Any], solver_id: str) -> dict[str, Any]:
    """
    Optional mapping hook: remap material for a solver using catalog definitions.

    If no mapping exists, returns the material unchanged.
    """
    if not isinstance(material, dict):
        return material
    model_name = str(material.get("model_name", "")).strip()
    model = mc.model_by_name(model_name)
    if model is None or not isinstance(model.solver_mapping, dict):
        return material
    mapping = model.solver_mapping.get(solver_id)
    if not isinstance(mapping, dict):
        return material
    out = copy.deepcopy(material)
    mapped_model = mapping.get("model_name")
    if isinstance(mapped_model, str) and mapped_model:
        out["model_name"] = mapped_model
    mapped_behavior = mapping.get("behavior")
    if isinstance(mapped_behavior, str) and mapped_behavior:
        out["behavior"] = mapped_behavior
    params = material.get("parameters", {})
    if not isinstance(params, dict):
        params = {}
    param_map = mapping.get("params")
    if isinstance(param_map, dict):
        new_params: dict[str, Any] = {}
        for target_key, source_path in param_map.items():
            if not isinstance(target_key, str) or not isinstance(source_path, str):
                continue
            new_params[target_key] = _get_path(params, source_path)
        out["parameters"] = new_params
    return out
