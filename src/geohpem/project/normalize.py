from __future__ import annotations

from typing import Any

from geohpem.geometry.polygon2d import Polygon2D
from geohpem.util.ids import new_uid


def ensure_request_ids(request: dict[str, Any], mesh: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Ensure stable IDs exist for key project objects.

    - stages[*].uid
    - materials[*].uid
    - geometry polygon vertex_ids/edge_ids
    - (optional) sets metadata in request["sets_meta"] keyed by NPZ keys (for UI only)

    Returns the (possibly) mutated request dict for convenience.
    """
    # stages
    stages = request.get("stages")
    if isinstance(stages, list):
        for s in stages:
            if isinstance(s, dict) and not s.get("uid"):
                s["uid"] = new_uid("stage")

    # materials
    mats = request.get("materials")
    if isinstance(mats, dict):
        for _mid, m in mats.items():
            if isinstance(m, dict) and not m.get("uid"):
                m["uid"] = new_uid("mat")

    # geometry: polygon2d
    geo = request.get("geometry")
    if isinstance(geo, dict) and geo.get("type") == "polygon2d":
        try:
            poly = Polygon2D.from_dict(geo)
        except Exception:
            poly = None
        if poly is not None:
            n = len(poly.vertices)
            v_ids = geo.get("vertex_ids")
            e_ids = geo.get("edge_ids")
            if not isinstance(v_ids, list) or len(v_ids) != n:
                geo["vertex_ids"] = [new_uid("v") for _ in range(n)]
            if not isinstance(e_ids, list) or len(e_ids) != n:
                geo["edge_ids"] = [new_uid("e") for _ in range(n)]

    # sets meta (UI-only, does not affect solver contract)
    if mesh is not None and isinstance(mesh, dict):
        sets_meta = request.get("sets_meta")
        if not isinstance(sets_meta, dict):
            sets_meta = {}
            request["sets_meta"] = sets_meta
        for k in mesh.keys():
            if not (k.startswith("node_set__") or k.startswith("edge_set__") or k.startswith("elem_set__")):
                continue
            if k not in sets_meta or not isinstance(sets_meta.get(k), dict) or not sets_meta[k].get("uid"):
                sets_meta[k] = {
                    "uid": new_uid("set"),
                    "label": k,  # display label can be edited later without renaming NPZ key
                }

    return request


def find_stage_index_by_uid(request: dict[str, Any], uid: str) -> int | None:
    stages = request.get("stages")
    if not isinstance(stages, list):
        return None
    for i, s in enumerate(stages):
        if isinstance(s, dict) and s.get("uid") == uid:
            return i
    return None

